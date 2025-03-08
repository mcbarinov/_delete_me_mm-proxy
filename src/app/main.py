from fastapi import FastAPI
from mm_base5 import init_server

from app import settings
from app.core.core import Core
from app.server.jinja import custom_jinja


def start() -> FastAPI:
    core = Core(settings.core_config)
    core.startup()
    return init_server(core, settings.server_config, custom_jinja, settings.get_router())
