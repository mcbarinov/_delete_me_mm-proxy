from typing import Self

from mm_base6 import BaseCore, CoreConfig

from app.core.db import Db
from app.core.services.proxy import ProxyService
from app.core.services.source import SourceService
from app.settings import DynamicConfigs, DynamicSettings


class ServiceRegistry:
    proxy: ProxyService
    source: SourceService


class Core(BaseCore[DynamicConfigs, DynamicSettings, Db, ServiceRegistry]):
    @classmethod
    async def init(cls, core_config: CoreConfig) -> Self:
        res = await super().base_init(core_config, DynamicConfigs, DynamicSettings, Db, ServiceRegistry)
        res.services.proxy = ProxyService(res.base_service_params)
        res.services.source = SourceService(res.base_service_params)
        return res

    async def configure_scheduler(self) -> None:
        self.scheduler.add_task("proxy_check", 1, self.services.proxy.check_next)
        self.scheduler.add_task("source_check", 60, self.services.source.check_next)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
