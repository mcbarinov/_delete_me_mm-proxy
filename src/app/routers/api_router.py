from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Query
from starlette.responses import PlainTextResponse, Response

from app.app import App


def init(app: App) -> APIRouter:
    router = APIRouter()

    @router.get("/sources")
    def get_sources():
        raise NotImplementedError

    @router.get("/sources/{pk}")
    def get_source(pk: str):
        return app.db.source.get(pk)

    @router.delete("/sources/{pk}")
    def delete_source(pk: str):
        app.db.proxy.delete_many({"source": pk})
        return app.db.source.delete(pk)

    @router.post("/sources/{pk}/check")
    def check_source(pk: str):
        return app.main_service.check_source(pk)

    @router.post("/sources/{pk}/clear-default")
    def clear_default(pk: str):
        return app.db.source.set(pk, {"default": None})

    @router.post("/sources/{pk}/delete-proxies")
    def delete_proxies_for_source(pk: str):
        return app.db.proxy.delete_many({"source": pk})

    @router.get("/proxies/live")
    def get_live_proxies(sources: str | None = None, format_: Annotated[str, Query(alias="format")] = "json"):
        proxies = app.main_service.get_live_proxies(sources.split(",") if sources else None)
        if format_ == "text":
            return Response(content="\n".join([p.url for p in proxies]), media_type="text/plain")

        return {"proxies": [p.url for p in proxies]}

    @router.get("/proxies/{pk}")
    def get_proxy(pk: ObjectId):
        return app.db.proxy.get(pk)

    @router.get("/proxies/{pk}/url", response_class=PlainTextResponse)
    def get_proxy_url(pk: ObjectId):
        return app.db.proxy.get(pk).url

    @router.post("/proxies/{pk}/check")
    def check_proxy(pk: ObjectId):
        return app.main_service.check_proxy(pk)

    return router
