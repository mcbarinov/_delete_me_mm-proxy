from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Query
from starlette.responses import JSONResponse, PlainTextResponse, Response

from app.core.db import Proxy
from app.server.deps import CoreDep

router = APIRouter(prefix="/api/proxies", tags=["proxy"])


@router.get("/live")
def get_live_proxies(
    core: CoreDep, sources: str | None = None, format_: Annotated[str, Query(alias="format")] = "json"
) -> Response:
    proxies = core.proxy_service.get_live_proxies(sources.split(",") if sources else None)
    proxy_urls = [p.url for p in proxies]
    if format_ == "text":
        return Response(content="\n".join(proxy_urls), media_type="text/plain")

    return JSONResponse({"proxies": proxy_urls}, media_type="application/json")


@router.get("/{id}")
def get_proxy(core: CoreDep, id: ObjectId) -> Proxy:
    return core.db.proxy.get(id)


@router.get("/{id}/url", response_class=PlainTextResponse)
def get_proxy_url(core: CoreDep, id: ObjectId) -> str:
    return core.db.proxy.get(id).url


@router.post("/{id}/check")
def check_proxy(core: CoreDep, id: ObjectId) -> dict[str, object]:
    return core.proxy_service.check(id)
