import asyncio
import contextlib
import logging
from urllib.parse import urlparse

import pydash
from bson import ObjectId
from mm_base6 import Service
from mm_concurrency import async_synchronized
from mm_http import http_request
from mm_mongo import MongoUpdateResult
from mm_std import utc_delta, utc_now

from app.core.db import Protocol, Proxy, ProxyType, Status
from app.core.types import AppCore
from app.core.utils import AsyncSlidingWindowCounter

logger = logging.getLogger(__name__)


class ProxyService(Service[AppCore]):
    def __init__(self) -> None:
        super().__init__()
        self.counter = AsyncSlidingWindowCounter(window_seconds=60)  # how many proxy checks per minute

    async def on_startup(self) -> None:
        await self.refresh_own_ip()

    def configure_scheduler(self) -> None:
        self.core.scheduler.add_task("proxy_check", 1, self.core.services.proxy.check_next)

    async def refresh_own_ip(self) -> str | None:
        res = await http_request("https://api.ipify.org/?format=json", timeout=10)
        ip: str | None = res.parse_json("ip", none_on_error=True)
        if ip:
            self.core.state.own_ip = ip
            logger.info("own_ip detected: %s", ip)
        return ip

    async def check(self, id: ObjectId) -> dict[str, object]:
        proxy = await self.core.db.proxy.get(id)
        logger.debug("check proxy", extra={"id": proxy.id, "url": proxy.url})

        response_ip = await get_proxy_response_ip(proxy.url, self.core.settings.proxy_check_timeout)
        success, proxy_ip = self._validate_proxy_response(proxy, response_ip)

        await self.counter.record_operation()

        status = Status.OK if success else Status.DOWN
        updated: dict[str, object] = {"status": status, "checked_at": utc_now()}
        if success:
            updated["last_ok_at"] = utc_now()
            if proxy_ip:
                updated["proxy_ip"] = proxy_ip
        updated["check_history"] = ([success, *proxy.check_history])[:100]

        updated_proxy = await self.core.db.proxy.set_and_get(id, updated)
        if updated_proxy.is_time_to_delete():
            await self.core.db.proxy.delete(id)
            updated["deleted"] = True

        return updated

    def _validate_proxy_response(self, proxy: Proxy, response_ip: str | None) -> tuple[bool, str | None]:
        if not response_ip:
            return False, None

        # Protection: if response is our own IP — proxy is not working
        if response_ip == self.core.state.own_ip:
            return False, None

        if proxy.type == ProxyType.DIRECT:
            # For direct: verify IP matches hostname from URL
            expected_ip = urlparse(proxy.url).hostname
            if response_ip != expected_ip:
                return False, None

        # Gateway: any IP (except our own) = OK
        return True, response_ip

    @async_synchronized
    async def check_next(self) -> None:
        if not self.core.settings.proxies_check:
            return
        limit = self.core.settings.max_proxies_check
        proxies = await self.core.db.proxy.find({"checked_at": None}, limit=limit)
        if len(proxies) < limit:
            proxies += await self.core.db.proxy.find(
                {"checked_at": {"$lt": utc_delta(minutes=-5)}}, "checked_at", limit=limit - len(proxies)
            )

        async with asyncio.TaskGroup() as tg:
            for proxy in proxies:
                tg.create_task(self.check(proxy.id), name=f"check_proxy_{proxy.id}")

    async def get_live_proxies(
        self, sources: list[str] | None, protocol: Protocol | None = None, unique_ip: bool = False
    ) -> list[Proxy]:
        query = {
            "status": Status.OK,
            "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.core.settings.live_last_ok_minutes)},
        }
        if sources:
            query["source"] = {"$in": sources}
        if protocol:
            query["protocol"] = protocol.value
        proxies = await self.core.db.proxy.find(query, "url")
        if unique_ip:
            with_ip = [p for p in proxies if p.proxy_ip]
            without_ip = [p for p in proxies if not p.proxy_ip]
            unique_with_ip = pydash.uniq_by(with_ip, lambda p: p.proxy_ip)
            proxies = unique_with_ip + without_ip
        return proxies

    async def reset_all_proxies_status(self) -> MongoUpdateResult:
        return await self.core.db.proxy.update_many(
            {}, {"$set": {"status": Status.UNKNOWN, "checked_at": None, "last_ok_at": None}}
        )


async def get_proxy_response_ip(proxy: str, timeout: float) -> str | None:
    tasks = [
        asyncio.create_task(httpbin_get_ip(proxy, timeout)),
        asyncio.create_task(ipify_get_ip(proxy, timeout)),
    ]
    try:
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await t
                return result
        return None
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t


async def httpbin_get_ip(proxy: str, timeout: float) -> str | None:
    res = await http_request("https://httpbin.org/ip", proxy=proxy, timeout=timeout)
    ip: str | None = res.parse_json("origin", none_on_error=True)
    return ip


async def ipify_get_ip(proxy: str, timeout: float) -> str | None:
    res = await http_request("https://api.ipify.org/?format=json", proxy=proxy, timeout=timeout)
    ip: str | None = res.parse_json("ip", none_on_error=True)
    return ip
