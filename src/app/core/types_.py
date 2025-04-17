from mm_base6 import BaseService, BaseServiceParams

from app.core.db import Db
from app.settings import DynamicConfigs, DynamicSettings

AppService = BaseService[DynamicConfigs, DynamicSettings, Db]
AppServiceParams = BaseServiceParams[DynamicConfigs, DynamicSettings, Db]
