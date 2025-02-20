import contextlib
import re

from bson import ObjectId
from mm_std import ConcurrentTasks, hr, synchronized, utc_delta, utc_now
from pydantic import BaseModel
from pymongo.errors import BulkWriteError

from app.models import Proxy, Status
from app.services.base import AppService, AppServiceParams


class Stats(BaseModel):
    class Count(BaseModel):
        all: int
        ok: int
        live: int

    all: Count
    sources: dict[str, Count]  # source_id -> Count


class MainService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)

    def check_source(self, pk: str) -> int:
        source = self.db.source.get(pk)
        urls = []

        # collect from items
        for item in source.items:
            if item.startswith(("http://", "socks5://")):
                urls.append(item)
            elif source.default:  # check item is ipv4
                urls.append(source.default.url(item))

        # collect from link
        if source.link and source.default:
            res = hr(source.link, timeout=10)
            ip_addresses = parse_ipv4_addresses(res.body)
            new_urls = [source.default.url(item) for item in ip_addresses]
            urls.extend(new_urls)

        proxies = [Proxy.new(pk, url) for url in urls]
        if proxies:
            with contextlib.suppress(BulkWriteError):
                self.db.proxy.insert_many(proxies, ordered=False)

        self.db.source.set(pk, {"checked_at": utc_now()})

        return len(proxies)

    def check_proxy(self, pk: ObjectId) -> dict[str, object]:
        proxy = self.db.proxy.get(pk)
        res = hr("https://httpbin.org/ip", proxy=proxy.url, timeout=5)
        status = Status.OK if res.json and res.json.get("origin") == proxy.ip else Status.DOWN

        updated = {"status": status, "checked_at": utc_now()}
        if status == Status.OK:
            updated["last_ok_at"] = utc_now()
        updated["check_history"] = ([status == Status.OK, *proxy.check_history])[:100]

        updated_proxy = self.db.proxy.set_and_get(pk, updated)
        if updated_proxy.is_time_to_delete():
            self.db.proxy.delete(pk)
            updated["deleted"] = True

        return updated

    @synchronized
    def next_check_source(self) -> None:
        source = self.db.source.find_one(
            {"$or": [{"checked_at": None}, {"checked_at": {"$lt": utc_delta(hours=-1)}}]},
            "checked_at",
        )
        if source:
            self.check_source(source.id)

    @synchronized
    def next_check_proxies(self) -> None:
        proxies = self.db.proxy.find(
            {"$or": [{"checked_at": None}, {"checked_at": {"$lt": utc_delta(minutes=-5)}}]},
            "checked_at",
            limit=15,
        )

        tasks = ConcurrentTasks(max_workers=15)
        for p in proxies:
            tasks.add_task(f"check_proxy_{p.id}", self.check_proxy, args=(p.id,))
        tasks.execute()

    def get_live_proxies(self, sources: list[str] | None) -> list[Proxy]:
        query = {"status": Status.OK, "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dconfig.live_last_ok_minutes)}}
        if sources:
            query["source"] = {"$in": sources}
        return self.db.proxy.find(query, "url")

    def calc_stats(self) -> Stats:
        all_ = Stats.Count(
            all=self.db.proxy.count({}),
            ok=self.db.proxy.count({"status": Status.OK}),
            live=self.db.proxy.count(
                {"status": Status.OK, "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dconfig.live_last_ok_minutes)}}
            ),
        )
        sources = {}
        for source in self.db.source.find({}, "_id"):
            sources[source.id] = Stats.Count(
                all=self.db.proxy.count({"source": source.id}),
                ok=self.db.proxy.count({"source": source.id, "status": Status.OK}),
                live=self.db.proxy.count(
                    {
                        "source": source.id,
                        "status": Status.OK,
                        "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dconfig.live_last_ok_minutes)},
                    }
                ),
            )
        return Stats(all=all_, sources=sources)


def parse_ipv4_addresses(data: str) -> set[str]:
    result = set()
    for line in data.split("\n"):
        line = line.lower().strip()  # noqa: PLW2901
        m = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", line)
        if m:
            result.add(line)
    return result
