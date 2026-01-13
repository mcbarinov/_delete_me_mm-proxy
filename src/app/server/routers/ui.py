from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.params import Query
from mm_base6 import cbv, redirect
from mm_std import parse_lines, replace_empty_dict_entries
from pydantic import BaseModel
from starlette.responses import HTMLResponse, RedirectResponse

from app.core.db import Protocol, Source, Status
from app.core.types import AppView

router = APIRouter(include_in_schema=False)


@cbv(router)
class PageCBV(AppView):
    @router.get("/")
    async def index(self) -> HTMLResponse:
        return await self.render.html("index.j2")

    @router.get("/bot")
    async def bot(self) -> HTMLResponse:
        checks_per_minute = await self.core.services.proxy.counter.get_count()
        return await self.render.html("bot.j2", checks_per_minute=checks_per_minute)

    @router.get("/sources")
    async def sources_page(self) -> HTMLResponse:
        stats = await self.core.services.source.calc_stats()
        sources = await self.core.db.source.find({}, "_id")
        return await self.render.html("sources.j2", stats=stats, sources=sources)

    @router.get("/proxies")
    async def proxies_page(
        self,
        source: Annotated[str | None, Query()] = None,
        status: Annotated[str | None, Query()] = None,
        protocol: Annotated[str | None, Query()] = None,
    ) -> HTMLResponse:
        query = replace_empty_dict_entries({"source": source, "status": status, "protocol": protocol})
        proxies = await self.core.db.proxy.find(query, "proxy_ip")
        sources = [s.id for s in await self.core.db.source.find({}, "_id")]
        statuses = [s.value for s in list(Status)]
        protocols = [p.value for p in list(Protocol)]
        return await self.render.html(
            "proxies.j2", proxies=proxies, sources=sources, statuses=statuses, protocols=protocols, query=query
        )


@cbv(router)
class ActionCBV(AppView):
    @router.post("/sources")
    async def create_source(self, id: Annotated[str, Form()], link: Annotated[str | None, Form()] = None) -> RedirectResponse:
        await self.core.db.source.insert_one(Source(id=id, link=link))
        self.render.flash("Source created successfully")
        return redirect("/sources")

    @router.post("/sources/import")
    async def import_sources(self, toml: Annotated[str, Form()]) -> RedirectResponse:
        imported_sources = await self.core.services.source.import_from_toml(toml)
        self.render.flash(f"Sources imported successfully: {imported_sources}")
        return redirect("/sources")

    @router.post("/sources/{id}/items")
    async def set_source_items(self, id: str, items: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.db.source.set(id, {"items": parse_lines(items, deduplicate=True)})
        self.render.flash("Source items updated successfully")
        return redirect("/sources")

    class SetDefaultForm(BaseModel):
        protocol: Protocol
        username: str
        password: str
        port: int

    @router.post("/sources/{id}/default")
    async def set_source_default(self, id: str, form: Annotated[SetDefaultForm, Form()]) -> RedirectResponse:
        await self.core.db.source.set(id, {"default": form.model_dump()})
        self.render.flash("Source default updated successfully")
        return redirect("/sources")
