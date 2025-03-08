from typing import Annotated

from fastapi import APIRouter, Form
from mm_base5 import RenderDep, redirect
from mm_std import str_to_list
from pydantic import BaseModel
from starlette.responses import HTMLResponse, RedirectResponse

from app.core.db import Protocol, Source
from app.server.deps import CoreDep

router = APIRouter(include_in_schema=False)


@router.get("/")
def index_page(render: RenderDep) -> HTMLResponse:
    return render.html("index.j2")


@router.get("/sources")
def sources_page(render: RenderDep, core: CoreDep) -> HTMLResponse:
    stats = core.source_service.calc_stats()
    sources = core.db.source.find({}, "_id")
    return render.html("sources.j2", stats=stats, sources=sources)


@router.get("/proxies")
def proxies_page(render: RenderDep, core: CoreDep) -> HTMLResponse:
    proxies = core.db.proxy.find({}, "ip")
    return render.html("proxies.j2", proxies=proxies)


# ACTIONS


@router.post("/sources")
def create_source(
    render: RenderDep, core: CoreDep, id: Annotated[str, Form()], link: Annotated[str | None, Form()] = None
) -> RedirectResponse:
    core.db.source.insert_one(Source(id=id, link=link))
    render.flash("Source created successfully")
    return redirect("/sources")


@router.post("/sources/{id}/items")
def set_source_items(render: RenderDep, core: CoreDep, id: str, items: Annotated[str, Form()]) -> RedirectResponse:
    core.db.source.set(id, {"items": str_to_list(items, unique=True)})
    render.flash("Source items updated successfully")
    return redirect("/sources")


class SetDefaultForm(BaseModel):
    protocol: Protocol
    username: str
    password: str
    port: int


@router.post("/sources/{id}/default")
def set_source_default(render: RenderDep, core: CoreDep, id: str, form: Annotated[SetDefaultForm, Form()]) -> RedirectResponse:
    core.db.source.set(id, {"default": form.model_dump()})
    render.flash("Source default updated successfully")
    return redirect("/sources")
