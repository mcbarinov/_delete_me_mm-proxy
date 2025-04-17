import contextlib
import logging
import re

import pydash
from mm_base6 import UserError
from mm_mongo import MongoDeleteResult, MongoInsertOneResult
from mm_std import async_synchronized, http_request, toml_dumps, toml_loads, utc_delta, utc_now
from pydantic import BaseModel
from pymongo.errors import BulkWriteError

from app.core.db import Proxy, Source, Status
from app.core.types_ import AppService, AppServiceParams


class Stats(BaseModel):
    class Count(BaseModel):
        all: int
        ok: int
        live: int

    all: Count
    sources: dict[str, Count]  # source_id -> Count


logger = logging.getLogger(__name__)


class SourceService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)

    async def create(self, id: str, link: str | None = None) -> MongoInsertOneResult:
        return await self.db.source.insert_one(Source(id=id, link=link))

    async def delete(self, id: str) -> MongoDeleteResult:
        await self.db.proxy.delete_many({"source": id})
        return await self.db.source.delete(id)

    async def calc_stats(self) -> Stats:
        all_uniq_ip = await self.db.proxy.collection.distinct("ip", {})
        ok_uniq_ip = await self.db.proxy.collection.distinct("ip", {"status": Status.OK})
        live_uniq_ip = await self.db.proxy.collection.distinct(
            "ip", {"status": Status.OK, "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dynamic_configs.live_last_ok_minutes)}}
        )

        all_ = Stats.Count(all=len(all_uniq_ip), ok=len(ok_uniq_ip), live=len(live_uniq_ip))
        sources = {}
        for source in await self.db.source.find({}, "_id"):
            sources[source.id] = Stats.Count(
                all=await self.db.proxy.count({"source": source.id}),
                ok=await self.db.proxy.count({"source": source.id, "status": Status.OK}),
                live=await self.db.proxy.count(
                    {
                        "source": source.id,
                        "status": Status.OK,
                        "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dynamic_configs.live_last_ok_minutes)},
                    }
                ),
            )
        return Stats(all=all_, sources=sources)

    async def check(self, id: str) -> int:
        logger.debug("check source", extra={"id": id})
        source = await self.db.source.get(id)
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
            if res.is_error():
                logger.warning("Failed to fetch source link", extra={"link": source.link, "response": res.to_dict()})
                return 0
            ip_addresses = parse_ipv4_addresses(res.body or "")
            new_urls = [source.default.url(item) for item in ip_addresses]
            urls.extend(new_urls)

        proxies = [Proxy.new(id, url) for url in urls]
        if proxies:
            with contextlib.suppress(BulkWriteError):
                await self.db.proxy.insert_many(proxies, ordered=False)

        await self.db.source.set(id, {"checked_at": utc_now()})

        return len(proxies)

    @async_synchronized
    async def check_next(self) -> None:
        source = await self.db.source.find_one(
            {"$or": [{"checked_at": None}, {"checked_at": {"$lt": utc_delta(hours=-1)}}]},
            "checked_at",
        )
        if source:
            await self.check(source.id)

    async def export_as_toml(self) -> str:
        sources = [s.model_dump(exclude={"created_at", "checked_at"}) for s in await self.db.source.find({})]
        sources = [pydash.rename_keys(s, {"_id": "id"}) for s in sources]
        return toml_dumps({"sources": sources})

    async def import_from_toml(self, toml: str) -> int:
        data = toml_loads(toml)
        try:
            sources = [Source(**source) for source in data.get("sources", [])]
        except Exception as e:
            raise UserError(f"Invalid toml data: {e}") from e

        for source in sources:
            await self.db.source.set(source.id, source.model_dump(exclude={"_id"}), upsert=True)

        return len(sources)


def parse_ipv4_addresses(data: str) -> set[str]:
    result = set()
    for line in data.split("\n"):
        line = line.lower().strip()  # noqa: PLW2901
        m = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", line)
        if m:
            result.add(line)
    return result
