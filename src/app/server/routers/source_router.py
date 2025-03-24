from fastapi import APIRouter
from mm_mongo import MongoDeleteResult, MongoUpdateResult
from starlette.responses import PlainTextResponse

from app.core.db import Source
from app.server.deps import CoreDep

router = APIRouter(prefix="/api/sources", tags=["source"])


@router.get("/export", response_class=PlainTextResponse)
async def export_sources(core: CoreDep) -> str:
    return await core.source_service.export_as_toml()


@router.get("/{id}")
async def get_source(core: CoreDep, id: str) -> Source:
    return await core.db.source.get(id)


@router.post("/{id}/check")
async def check_source(core: CoreDep, id: str) -> int:
    return await core.source_service.check(id)


@router.delete("/{id}/default")
async def delete_source_default(core: CoreDep, id: str) -> MongoUpdateResult:
    return await core.db.source.set(id, {"default": None})


@router.delete("/{id}")
async def delete_source(core: CoreDep, id: str) -> MongoDeleteResult:
    return await core.source_service.delete(id)


@router.delete("/{id}/proxies")
async def delete_source_proxies(core: CoreDep, id: str) -> MongoDeleteResult:
    return await core.db.proxy.delete_many({"source": id})
