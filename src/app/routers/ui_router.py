import pydash
from fastapi import APIRouter
from mm_base1.jinja import Templates, form_choices
from mm_base1.utils import depends_form
from starlette.requests import Request
from starlette.responses import HTMLResponse
from wtforms import Form, StringField
from wtforms import validators as fv
from wtforms.fields.choices import SelectField
from wtforms.fields.numeric import IntegerField
from wtforms.fields.simple import TextAreaField

from app.app import App
from app.models import Protocol, Source


class CreateSourceForm(Form):  # type: ignore[misc]
    id = StringField(validators=[fv.input_required()])
    link = StringField()


class SetItemsForm(Form):  # type: ignore[misc]
    items = TextAreaField(render_kw={"rows": 20})

    def parse_items(self) -> list[str]:
        result = []
        for line in self.data["items"].strip().split("\n"):
            line = line.strip()  # noqa: PLW2901
            if line:
                result.append(line)
        return pydash.uniq(result)


class SetDefaultForm(Form):  # type: ignore[misc]
    protocol = SelectField(choices=form_choices(Protocol))
    username = StringField(validators=[fv.input_required()])
    password = StringField(validators=[fv.input_required()])
    port = IntegerField(validators=[fv.input_required()])

    def parse(self) -> Source.Default:
        return Source.Default(
            protocol=self.data["protocol"], username=self.data["username"], password=self.data["password"], port=self.data["port"]
        )

    def set_values(self, default: Source.Default | None) -> None:
        if default:
            self.protocol.data = default.protocol
            self.username.data = default.username
            self.password.data = default.password
            self.port.data = default.port


def init(app: App, templates: Templates) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def index_page(req: Request):
        return templates.render(req, "index.j2")

    @router.get("/sources", response_class=HTMLResponse)
    def sources_page(req: Request):
        form = CreateSourceForm()
        sources = app.db.source.find({}, "_id")
        stats = app.main_service.calc_stats()
        return templates.render(
            req,
            "sources.j2",
            {"form": form, "sources": sources, "stats": stats},
        )

    @router.get("/set-items/{pk}", response_class=HTMLResponse)
    def set_items_page(req: Request, pk: str):
        source = app.db.source.get(pk)
        form = SetItemsForm()
        form.items.data = "\n".join(source.items)
        return templates.render(req, "set_items.j2", {"source": source, "form": form})

    @router.get("/set-default/{pk}", response_class=HTMLResponse)
    def set_default_page(req: Request, pk: str):
        source = app.db.source.get(pk)
        form = SetDefaultForm()
        form.set_values(source.default)
        return templates.render(req, "set_default.j2", {"source": source, "form": form})

    @router.get("/proxies", response_class=HTMLResponse)
    def proxies_page(req: Request):
        proxies = app.db.proxy.find({}, "ipv4")
        return templates.render(req, "proxies.j2", {"proxies": proxies})

    # actions
    @router.post("/create-source")
    def create_source(form_data=depends_form):
        form = CreateSourceForm(form_data)
        return app.db.source.insert_one(Source.new(form.data["id"], form.data["link"]))

    @router.post("/set-items/{pk}")
    def set_items(pk: str, form_data=depends_form):
        form = SetItemsForm(form_data)
        return app.db.source.set(pk, {"items": form.parse_items()})

    @router.post("/set-default/{pk}")
    def set_default(pk: str, form_data=depends_form):
        form = SetDefaultForm(form_data)
        return app.db.source.set(pk, {"default": form.parse().dict()})

    return router
