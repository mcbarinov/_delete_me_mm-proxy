from fastapi import APIRouter
from mm_base6 import cbv
from mm_mongo import MongoDeleteResult, MongoUpdateResult
from starlette.responses import PlainTextResponse

from app.core.db import Source
from app.core.types import AppView

router = APIRouter(prefix="/api/sources", tags=["source"])


@cbv(router)
class CBV(AppView):
    @router.get("/export", response_class=PlainTextResponse)
    async def export_sources(self) -> str:
        return await self.core.services.source.export_as_toml()

    @router.get("/{id}")
    async def get_source(self, id: str) -> Source:
        return await self.core.db.source.get(id)

    @router.post("/{id}/check")
    async def check_source(self, id: str) -> int:
        return await self.core.services.source.check(id)

    @router.delete("/{id}/default")
    async def delete_source_default(self, id: str) -> MongoUpdateResult:
        return await self.core.db.source.set(id, {"default": None})

    @router.delete("/{id}")
    async def delete_source(self, id: str) -> MongoDeleteResult:
        return await self.core.services.source.delete(id)

    @router.delete("/{id}/proxies")
    async def delete_source_proxies(self, id: str) -> MongoDeleteResult:
        return await self.core.db.proxy.delete_many({"source": id})
