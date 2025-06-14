from typing import TYPE_CHECKING

from mm_base6 import Core, View

if TYPE_CHECKING:
    from app.core.db import Db
    from app.core.services import ServiceRegistry
    from app.settings import DynamicConfigs, DynamicValues

    AppCore = Core[DynamicConfigs, DynamicValues, Db, ServiceRegistry]
    AppView = View[DynamicConfigs, DynamicValues, Db, ServiceRegistry]
else:
    # Runtime: use string forward references to avoid circular imports
    AppCore = Core["DynamicConfigs", "DynamicValues", "Db", "ServiceRegistry"]
    AppView = View["DynamicConfigs", "DynamicValues", "Db", "ServiceRegistry"]
