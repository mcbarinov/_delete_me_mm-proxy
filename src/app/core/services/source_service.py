import contextlib
import re

from mm_mongo import MongoDeleteResult, MongoInsertOneResult
from mm_std import ahr, async_synchronized, utc_delta, utc_now
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


class SourceService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)

    async def create(self, id: str, link: str | None = None) -> MongoInsertOneResult:
        return await self.db.source.insert_one(Source(id=id, link=link))

    async def delete(self, id: str) -> MongoDeleteResult:
        await self.db.proxy.delete_many({"source": id})
        return await self.db.source.delete(id)

    async def calc_stats(self) -> Stats:
        all_ = Stats.Count(
            all=await self.db.proxy.count({}),
            ok=await self.db.proxy.count({"status": Status.OK}),
            live=await self.db.proxy.count(
                {"status": Status.OK, "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dconfig.live_last_ok_minutes)}}
            ),
        )
        sources = {}
        for source in await self.db.source.find({}, "_id"):
            sources[source.id] = Stats.Count(
                all=await self.db.proxy.count({"source": source.id}),
                ok=await self.db.proxy.count({"source": source.id, "status": Status.OK}),
                live=await self.db.proxy.count(
                    {
                        "source": source.id,
                        "status": Status.OK,
                        "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dconfig.live_last_ok_minutes)},
                    }
                ),
            )
        return Stats(all=all_, sources=sources)

    async def check(self, pk: str) -> int:
        source = await self.db.source.get(pk)
        urls = []

        # collect from items
        for item in source.items:
            if item.startswith(("http://", "socks5://")):
                urls.append(item)
            elif source.default:  # check item is ipv4
                urls.append(source.default.url(item))

        # collect from link
        if source.link and source.default:
            res = await ahr(source.link, timeout=10)
            ip_addresses = parse_ipv4_addresses(res.body)
            new_urls = [source.default.url(item) for item in ip_addresses]
            urls.extend(new_urls)

        proxies = [Proxy.new(pk, url) for url in urls]
        if proxies:
            with contextlib.suppress(BulkWriteError):
                await self.db.proxy.insert_many(proxies, ordered=False)

        await self.db.source.set(pk, {"checked_at": utc_now()})

        return len(proxies)

    @async_synchronized
    async def check_next(self) -> None:
        source = await self.db.source.find_one(
            {"$or": [{"checked_at": None}, {"checked_at": {"$lt": utc_delta(hours=-1)}}]},
            "checked_at",
        )
        if source:
            await self.check(source.id)


def parse_ipv4_addresses(data: str) -> set[str]:
    result = set()
    for line in data.split("\n"):
        line = line.lower().strip()  # noqa: PLW2901
        m = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", line)
        if m:
            result.add(line)
    return result
