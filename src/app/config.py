from mm_base1.config import BaseAppConfig
from mm_base1.services.dconfig_service import DC, DConfigStorage
from mm_base1.services.dvalue_service import DValueStorage


class AppConfig(BaseAppConfig):
    tags: list[str] = ["main"]
    main_menu: dict[str, str] = {"/sources": "sources", "/proxies": "proxies"}


class DConfigSettings(DConfigStorage):
    live_last_ok_minutes = DC(15, "live proxies only if they checked less than this minutes ago")


class DValueSettings(DValueStorage):
    pass
