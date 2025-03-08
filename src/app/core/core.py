from mm_base5 import BaseCore, CoreConfig

from app.core.db import Db
from app.core.services.proxy_service import ProxyService
from app.core.services.source_service import SourceService
from app.settings import DConfigSettings, DValueSettings


class Core(BaseCore[DConfigSettings, DValueSettings, Db]):
    def __init__(self, core_config: CoreConfig) -> None:
        super().__init__(core_config, DConfigSettings, DValueSettings, Db)
        self.source_service: SourceService = SourceService(self.base_service_params)
        self.proxy_service: ProxyService = ProxyService(self.base_service_params)

        self.scheduler.add_job(self.source_service.check_next, 60)
        self.scheduler.add_job(self.proxy_service.check_next, 5)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
