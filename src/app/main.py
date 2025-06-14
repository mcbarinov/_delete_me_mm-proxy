import asyncio

from mm_base6 import Core, run

from app import settings
from app.core.db import Db
from app.core.services import ServiceRegistry
from app.server import jinja


async def main() -> None:
    core = await Core.init(
        core_config=settings.core_config,
        dynamic_configs_cls=settings.DynamicConfigs,
        dynamic_values_cls=settings.DynamicValues,
        db_cls=Db,
        service_registry_cls=ServiceRegistry,
        configure_scheduler_fn=settings.configure_scheduler,
        start_core_fn=settings.start_core,
        stop_core_fn=settings.stop_core,
    )

    await run(
        core=core,
        server_config=settings.server_config,
        telegram_handlers=None,
        router=settings.get_router(),
        jinja_config=jinja.jinja_config,
        host="0.0.0.0",  # noqa: S104 # nosec
        port=3000,
        uvicorn_log_level="warning",
    )


if __name__ == "__main__":
    asyncio.run(main())
