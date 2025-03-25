from __future__ import annotations

from typing import cast

from mm_base6 import BaseCore, CoreConfig

from app.core.db import Db
from app.core.services.proxy_service import ProxyService
from app.core.services.source_service import SourceService
from app.settings import DConfigSettings, DValueSettings


class Core(BaseCore[DConfigSettings, DValueSettings, Db]):
    proxy_service: ProxyService
    source_service: SourceService

    @classmethod
    async def init(cls, core_config: CoreConfig) -> Core:
        res = cast(Core, await super().base_init(core_config, DConfigSettings, DValueSettings, Db))
        res.proxy_service = ProxyService(res.base_service_params)
        res.source_service = SourceService(res.base_service_params)

        res.scheduler.add_task("proxy_check", 1, res.proxy_service.check_next)
        res.scheduler.add_task("source_check", 60, res.source_service.check_next)

        return res
