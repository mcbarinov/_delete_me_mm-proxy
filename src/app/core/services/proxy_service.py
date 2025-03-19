from bson import ObjectId
from mm_std import ConcurrentTasks, hr, synchronized, utc_delta, utc_now

from app.core.db import Proxy, Status
from app.core.types_ import AppService, AppServiceParams


class ProxyService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)

    def check(self, id: ObjectId) -> dict[str, object]:
        proxy = self.db.proxy.get(id)

        tasks = ConcurrentTasks()
        tasks.add_task("httpbin", httpbin_check, args=(proxy.ip, proxy.url))
        tasks.add_task("ipify", ipify_check, args=(proxy.ip, proxy.url))
        tasks.execute()

        status = Status.OK if tasks.result.get("httpbin", False) or tasks.result.get("ipify", False) else Status.DOWN

        updated = {"status": status, "checked_at": utc_now()}
        if status == Status.OK:
            updated["last_ok_at"] = utc_now()
        updated["check_history"] = ([status == Status.OK, *proxy.check_history])[:100]

        updated_proxy = self.db.proxy.set_and_get(id, updated)
        if updated_proxy.is_time_to_delete():
            self.db.proxy.delete(id)
            updated["deleted"] = True

        return updated

    @synchronized
    def check_next(self) -> None:
        proxies = self.db.proxy.find(
            {"$or": [{"checked_at": None}, {"checked_at": {"$lt": utc_delta(minutes=-5)}}]},
            "checked_at",
            limit=15,
        )

        tasks = ConcurrentTasks(max_workers=15)
        for p in proxies:
            tasks.add_task(f"check_proxy_{p.id}", self.check, args=(p.id,))
        tasks.execute()

    def get_live_proxies(self, sources: list[str] | None) -> list[Proxy]:
        query = {"status": Status.OK, "last_ok_at": {"$gt": utc_delta(minutes=-1 * self.dconfig.live_last_ok_minutes)}}
        if sources:
            query["source"] = {"$in": sources}
        return self.db.proxy.find(query, "url")


def httpbin_check(ip: str, proxy: str) -> bool:
    res = hr("https://httpbin.org/ip", proxy=proxy, timeout=5)
    return res.json.get("origin", None) == ip  # type: ignore[no-any-return]


def ipify_check(ip: str, proxy: str) -> bool:
    res = hr("https://api.ipify.org/?format=json", proxy=proxy, timeout=5)
    return res.json.get("ip", None) == ip  # type: ignore[no-any-return]
