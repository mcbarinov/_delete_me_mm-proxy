from fastapi import APIRouter
from mm_base6 import DC, CoreConfig, DConfigModel, DValueModel, ServerConfig

core_config = CoreConfig()

server_config = ServerConfig()
server_config.tags = ["source", "proxy"]
server_config.main_menu = {"/sources": "sources", "/proxies": "proxies"}


class DConfigSettings(DConfigModel):
    live_last_ok_minutes = DC(15, "live proxies only if they checked less than this minutes ago")
    max_proxies_check = DC(30, "max proxies to check in one iteration")


class DValueSettings(DValueModel):
    pass


def get_router() -> APIRouter:
    from app.server.routers import proxy_router, source_router, ui_router

    router = APIRouter()
    router.include_router(ui_router.router)
    router.include_router(source_router.router)
    router.include_router(proxy_router.router)
    return router
