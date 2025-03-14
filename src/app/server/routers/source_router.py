from fastapi import APIRouter
from mm_mongo import MongoDeleteResult, MongoUpdateResult

from app.core.db import Source
from app.server.deps import CoreDep

router = APIRouter(prefix="/api/sources", tags=["source"])


@router.get("/{id}")
def get_source(core: CoreDep, id: str) -> Source:
    return core.db.source.get(id)


@router.post("/{id}/check")
def check_source(core: CoreDep, id: str) -> int:
    return core.source_service.check(id)


@router.delete("/{id}/default")
def delete_source_default(core: CoreDep, id: str) -> MongoUpdateResult:
    return core.db.source.set(id, {"default": None})


@router.delete("/{id}")
def delete_source(core: CoreDep, id: str) -> MongoDeleteResult:
    return core.source_service.delete(id)


@router.delete("/{id}/proxies")
def delete_source_proxies(core: CoreDep, id: str) -> MongoDeleteResult:
    return core.db.proxy.delete_many({"source": id})
