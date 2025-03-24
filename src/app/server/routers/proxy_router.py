from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Query
from starlette.responses import JSONResponse, PlainTextResponse, Response

from app.core.db import Protocol, Proxy
from app.server.deps import CoreDep

router = APIRouter(prefix="/api/proxies", tags=["proxy"])


@router.get("/live")
async def get_live_proxies(
    core: CoreDep,
    sources: str | None = None,
    unique_ip: bool = False,
    protocol: Protocol | None = None,
    format_: Annotated[str, Query(alias="format")] = "json",
) -> Response:
    proxies = await core.proxy_service.get_live_proxies(sources.split(",") if sources else None, protocol, unique_ip)
    proxy_urls = [p.url for p in proxies]
    if format_ == "text":
        return Response(content="\n".join(proxy_urls), media_type="text/plain")

    return JSONResponse({"proxies": proxy_urls}, media_type="application/json")


@router.get("/{id}")
async def get_proxy(core: CoreDep, id: ObjectId) -> Proxy:
    return await core.db.proxy.get(id)


@router.get("/{id}/url", response_class=PlainTextResponse)
async def get_proxy_url(core: CoreDep, id: ObjectId) -> str:
    return (await core.db.proxy.get(id)).url


@router.post("/{id}/check")
async def check_proxy(core: CoreDep, id: ObjectId) -> dict[str, object]:
    return await core.proxy_service.check(id)
