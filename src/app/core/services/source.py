import contextlib
import logging
import re
from dataclasses import dataclass

import pydash
from mm_base6 import Service, UserError
from mm_base6.core.utils import toml_dumps, toml_loads
from mm_concurrency import async_synchronized
from mm_http import http_request
from mm_mongo import MongoDeleteResult, MongoInsertOneResult
from mm_std import utc_delta, utc_now
from pydantic import BaseModel
from pymongo.errors import BulkWriteError

from app.core.db import Proxy, Source, Status
from app.core.types import AppCore


class Stats(BaseModel):
    class Count(BaseModel):
        all: int
        ok: int
        live: int

    all: Count
    sources: dict[str, Count]  # source_id -> Count


logger = logging.getLogger(__name__)


class SourceService(Service[AppCore]):
    def configure_scheduler(self) -> None:
        self.core.scheduler.add_task("source_check", 60, self.core.services.source.check_next)

    async def create(self, id: str, link: str | None = None) -> MongoInsertOneResult:
        return await self.core.db.source.insert_one(Source(id=id, link=link))

    async def delete(self, id: str) -> MongoDeleteResult:
        await self.core.db.proxy.delete_many({"source": id})
        return await self.core.db.source.delete(id)

    async def calc_stats(self) -> Stats:
        all_uniq_ip = await self.core.db.proxy.collection.distinct("proxy_ip", {"proxy_ip": {"$ne": None}})
        ok_uniq_ip = await self.core.db.proxy.collection.distinct("proxy_ip", {"status": Status.OK, "proxy_ip": {"$ne": None}})
        live_uniq_ip = await self.core.db.proxy.collection.distinct(
            "proxy_ip",
            {
                "status": Status.OK,
                "proxy_ip": {"$ne": None},
                "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.core.settings.live_last_ok_minutes)},
            },
        )

        all_ = Stats.Count(all=len(all_uniq_ip), ok=len(ok_uniq_ip), live=len(live_uniq_ip))
        sources = {}
        for source in await self.core.db.source.find({}, "_id"):
            sources[source.id] = Stats.Count(
                all=await self.core.db.proxy.count({"source": source.id}),
                ok=await self.core.db.proxy.count({"source": source.id, "status": Status.OK}),
                live=await self.core.db.proxy.count(
                    {
                        "source": source.id,
                        "status": Status.OK,
                        "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.core.settings.live_last_ok_minutes)},
                    }
                ),
            )
        return Stats(all=all_, sources=sources)

    async def check(self, id: str) -> int:
        logger.debug("check source", extra={"id": id})
        source = await self.core.db.source.get(id)
        urls = []

        # collect from items
        for item in source.items:
            if item.startswith(("http://", "socks5://")):
                urls.append(item)
            elif source.default:  # check item is ipv4
                urls.append(source.default.url(item))

        # collect from link
        if source.link and source.default:
            res = await http_request(source.link, timeout=10)
            if res.is_err():
                logger.warning("Failed to fetch source link", extra={"link": source.link, "response": res.model_dump()})
                return 0
            for ep in parse_proxy_endpoints(res.body or ""):
                if ep.url:
                    urls.append(ep.url)
                elif ep.ip:
                    urls.append(source.default.url(ep.ip, ep.port))

        proxies = [Proxy.new(id, url) for url in urls]
        if proxies:
            with contextlib.suppress(BulkWriteError):
                await self.core.db.proxy.insert_many(proxies, ordered=False)

        await self.core.db.source.set(id, {"checked_at": utc_now()})

        return len(proxies)

    @async_synchronized
    async def check_next(self) -> None:
        source = await self.core.db.source.find_one(
            {"$or": [{"checked_at": None}, {"checked_at": {"$lt": utc_delta(hours=-1)}}]},
            "checked_at",
        )
        if source:
            await self.check(source.id)

    async def export_as_toml(self) -> str:
        sources = [s.model_dump(exclude={"created_at", "checked_at"}) for s in await self.core.db.source.find({})]
        sources = [pydash.rename_keys(s, {"_id": "id"}) for s in sources]
        return toml_dumps({"sources": sources})

    async def import_from_toml(self, toml: str) -> int:
        data = toml_loads(toml)
        try:
            sources = [Source(**source) for source in data.get("sources", [])]
        except Exception as e:
            raise UserError(f"Invalid toml data: {e}") from e

        for source in sources:
            await self.core.db.source.set(source.id, source.model_dump(exclude={"_id"}), upsert=True)

        return len(sources)


@dataclass
class ParsedEndpoint:
    url: str | None = None  # full URL (protocol://usr:pass@host:port)
    ip: str | None = None  # IP address (for partial formats)
    port: int | None = None  # port (for ip:port format)


def parse_proxy_endpoints(data: str) -> list[ParsedEndpoint]:
    """Parse proxy endpoints from text.

    Supported formats:
    - protocol://usr:pass@host:port → ParsedEndpoint(url=...)
    - 1.2.3.4:8080 → ParsedEndpoint(ip="1.2.3.4", port=8080)
    - 1.2.3.4 → ParsedEndpoint(ip="1.2.3.4")
    """
    result = []
    for line in data.split("\n"):
        line = line.strip()  # noqa: PLW2901
        if not line:
            continue

        # Full URL
        if line.startswith(("http://", "socks5://")):
            result.append(ParsedEndpoint(url=line))
            continue

        # IP:port
        m = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)$", line)
        if m:
            result.append(ParsedEndpoint(ip=m.group(1), port=int(m.group(2))))
            continue

        # Pure IP
        m = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$", line)
        if m:
            result.append(ParsedEndpoint(ip=m.group(1)))

    return result
