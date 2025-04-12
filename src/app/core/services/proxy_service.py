import asyncio

import pydash
from bson import ObjectId
from mm_mongo import MongoUpdateResult
from mm_std import async_synchronized, hra, utc_delta, utc_now

from app.core.db import Protocol, Proxy, Status
from app.core.types_ import AppService, AppServiceParams
from app.core.utils import AsyncSlidingWindowCounter


class ProxyService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)
        self.counter = AsyncSlidingWindowCounter(window_seconds=60)  # how many proxy checks per minute

    async def check(self, id: ObjectId) -> dict[str, object]:
        # start = time.perf_counter()
        proxy = await self.db.proxy.get(id)

        async with asyncio.TaskGroup() as tg:
            r1 = tg.create_task(httpbin_check(proxy.ip, proxy.url, self.dconfig.proxy_check_timeout), name=f"httpbin_check_{id}")
            r2 = tg.create_task(ipify_check(proxy.ip, proxy.url, self.dconfig.proxy_check_timeout), name=f"ipify_check_{id}")

        await self.counter.record_operation()

        status = Status.OK if r1 or r2 else Status.DOWN

        updated = {"status": status, "checked_at": utc_now()}
        if status == Status.OK:
            updated["last_ok_at"] = utc_now()
        updated["check_history"] = ([status == Status.OK, *proxy.check_history])[:100]

        updated_proxy = await self.db.proxy.set_and_get(id, updated)
        if updated_proxy.is_time_to_delete():
            await self.db.proxy.delete(id)
            updated["deleted"] = True

        # self.logger.debug("check proxy %s done in %.3f seconds", proxy.url, time.perf_counter() - start)
        return updated

    @async_synchronized
    async def check_next(self) -> None:
        if not self.dconfig.proxies_check:
            return
        limit = self.dconfig.max_proxies_check
        proxies = await self.db.proxy.find({"checked_at": None}, limit=limit)
        if len(proxies) < limit:
            proxies += await self.db.proxy.find(
                {"checked_at": {"$lt": utc_delta(minutes=-5)}}, "checked_at", limit=limit - len(proxies)
            )

        async with asyncio.TaskGroup() as tg:
            for proxy in proxies:
                tg.create_task(self.check(proxy.id), name=f"check_proxy_{proxy.id}")

    async def get_live_proxies(
        self, sources: list[str] | None, protocol: Protocol | None = None, unique_ip: bool = False
    ) -> list[Proxy]:
        query = {"status": Status.OK, "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dconfig.live_last_ok_minutes)}}
        if sources:
            query["source"] = {"$in": sources}
        if protocol:
            query["protocol"] = protocol.value
        proxies = await self.db.proxy.find(query, "url")
        if unique_ip:
            proxies = pydash.uniq_by(proxies, lambda p: p.ip)
        return proxies

    async def reset_all_proxies_status(self) -> MongoUpdateResult:
        return await self.db.proxy.update_many({}, {"$set": {"status": Status.UNKNOWN, "checked_at": None, "last_ok_at": None}})


async def httpbin_check(ip: str, proxy: str, timeout: float) -> bool:
    res = await hra("https://httpbin.org/ip", proxy=proxy, timeout=timeout)
    return res.json and res.json.get("origin", None) == ip  # type: ignore[no-any-return]


async def ipify_check(ip: str, proxy: str, timeout: float) -> bool:
    res = await hra("https://api.ipify.org/?format=json", proxy=proxy, timeout=timeout)
    return res.json and res.json.get("ip", None) == ip  # type: ignore[no-any-return]
