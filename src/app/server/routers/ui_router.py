from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.params import Query
from mm_base6 import RenderDep, redirect
from mm_std import replace_empty_dict_values, str_to_list
from pydantic import BaseModel
from starlette.responses import HTMLResponse, RedirectResponse

from app.core.db import Protocol, Source, Status
from app.server.deps import CoreDep

router = APIRouter(include_in_schema=False)


@router.get("/")
async def index_page(render: RenderDep) -> HTMLResponse:
    return await render.html("index.j2")


@router.get("/bot")
async def bot_page(render: RenderDep, core: CoreDep) -> HTMLResponse:
    checks_per_minute = await core.proxy_service.counter.get_count()
    return await render.html("bot.j2", checks_per_minute=checks_per_minute)


@router.get("/sources")
async def sources_page(render: RenderDep, core: CoreDep) -> HTMLResponse:
    stats = await core.source_service.calc_stats()
    sources = await core.db.source.find({}, "_id")
    return await render.html("sources.j2", stats=stats, sources=sources)


@router.get("/proxies")
async def proxies_page(
    render: RenderDep,
    core: CoreDep,
    source: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    protocol: Annotated[str | None, Query()] = None,
) -> HTMLResponse:
    query = replace_empty_dict_values({"source": source, "status": status, "protocol": protocol})
    proxies = await core.db.proxy.find(query, "ip")  # type: ignore[arg-type]
    sources = [s.id for s in await core.db.source.find({}, "_id")]
    statuses = [s.value for s in list(Status)]
    protocols = [p.value for p in list(Protocol)]
    return await render.html("proxies.j2", proxies=proxies, sources=sources, statuses=statuses, protocols=protocols, query=query)


# ACTIONS


@router.post("/sources")
async def create_source(
    render: RenderDep, core: CoreDep, id: Annotated[str, Form()], link: Annotated[str | None, Form()] = None
) -> RedirectResponse:
    await core.db.source.insert_one(Source(id=id, link=link))
    render.flash("Source created successfully")
    return redirect("/sources")


@router.post("/sources/import")
async def import_sources(render: RenderDep, core: CoreDep, toml: Annotated[str, Form()]) -> RedirectResponse:
    imported_sources = await core.source_service.import_from_toml(toml)
    render.flash(f"Sources imported successfully: {imported_sources}")
    return redirect("/sources")


@router.post("/sources/{id}/items")
async def set_source_items(render: RenderDep, core: CoreDep, id: str, items: Annotated[str, Form()]) -> RedirectResponse:
    await core.db.source.set(id, {"items": str_to_list(items, unique=True)})
    render.flash("Source items updated successfully")
    return redirect("/sources")


class SetDefaultForm(BaseModel):
    protocol: Protocol
    username: str
    password: str
    port: int


@router.post("/sources/{id}/default")
async def set_source_default(
    render: RenderDep, core: CoreDep, id: str, form: Annotated[SetDefaultForm, Form()]
) -> RedirectResponse:
    await core.db.source.set(id, {"default": form.model_dump()})
    render.flash("Source default updated successfully")
    return redirect("/sources")
