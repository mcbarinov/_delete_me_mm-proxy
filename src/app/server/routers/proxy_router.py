from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Query
from mm_base6 import cbv
from mm_mongo import MongoUpdateResult
from starlette.responses import JSONResponse, PlainTextResponse, Response

from app.core.db import Protocol, Proxy
from app.server.deps import View

router = APIRouter(prefix="/api/proxies", tags=["proxy"])


@cbv(router)
class CBV(View):
    @router.get("/live")
    async def get_live_proxies(
        self,
        sources: str | None = None,
        unique_ip: bool = False,
        protocol: Protocol | None = None,
        format_: Annotated[str, Query(alias="format")] = "json",
    ) -> Response:
        proxies = await self.core.proxy_service.get_live_proxies(sources.split(",") if sources else None, protocol, unique_ip)
        proxy_urls = [p.url for p in proxies]
        if format_ == "text":
            return Response(content="\n".join(proxy_urls), media_type="text/plain")

        return JSONResponse({"proxies": proxy_urls}, media_type="application/json")

    @router.post("/reset-status")
    async def reset_all_proxies_status(self) -> MongoUpdateResult:
        return await self.core.proxy_service.reset_all_proxies_status()

    @router.get("/{id}")
    async def get_proxy(self, id: ObjectId) -> Proxy:
        return await self.core.db.proxy.get(id)

    @router.get("/{id}/url", response_class=PlainTextResponse)
    async def get_proxy_url(self, id: ObjectId) -> str:
        return (await self.core.db.proxy.get(id)).url

    @router.post("/{id}/check")
    async def check_proxy(self, id: ObjectId) -> dict[str, object]:
        return await self.core.proxy_service.check(id)
