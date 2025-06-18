from typing import Annotated

from mm_base6 import CoreConfig, CoreLifecycle, ServerConfig, SettingsModel, StateModel, setting_field

from app.core.types import AppCore

core_config = CoreConfig()

server_config = ServerConfig()
server_config.tags = ["source", "proxy"]
server_config.main_menu = {"/bot": "bot", "/sources": "sources", "/proxies": "proxies"}


class Settings(SettingsModel):
    live_last_ok_minutes: Annotated[int, setting_field(15, "live proxies only if they checked less than this minutes ago")]
    proxies_check: Annotated[bool, setting_field(True, "enable periodic proxy check")]
    max_proxies_check: Annotated[int, setting_field(30, "max proxies to check in one iteration")]
    proxy_check_timeout: Annotated[float, setting_field(5.1, "timeout for proxy check")]


class State(StateModel):
    pass


class AppCoreLifecycle(CoreLifecycle[AppCore]):
    async def configure_scheduler(self) -> None:
        """Configure background scheduler tasks."""
        self.core.scheduler.add_task("proxy_check", 1, self.core.services.proxy.check_next)
        self.core.scheduler.add_task("source_check", 60, self.core.services.source.check_next)

    async def on_startup(self) -> None:
        """Startup logic for the application."""

    async def on_shutdown(self) -> None:
        """Cleanup logic for the application."""
