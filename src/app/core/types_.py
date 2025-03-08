from mm_base5 import BaseService, BaseServiceParams

from app.core.db import Db
from app.settings import DConfigSettings, DValueSettings

AppService = BaseService[DConfigSettings, DValueSettings, Db]
AppServiceParams = BaseServiceParams[DConfigSettings, DValueSettings, Db]
