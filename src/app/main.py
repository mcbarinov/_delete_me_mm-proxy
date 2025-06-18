import asyncio

from mm_base6 import Core, run

from app import config, telegram_handlers
from app.core.db import Db
from app.core.services import ServiceRegistry
from app.server import jinja


async def main() -> None:
    core = await Core.init(
        core_config=config.core_config,
        settings_cls=config.Settings,
        state_cls=config.State,
        db_cls=Db,
        service_registry_cls=ServiceRegistry,
        lifespan_cls=config.AppCoreLifecycle,
    )

    await run(
        core=core,
        server_config=config.server_config,
        telegram_handlers=telegram_handlers.handlers,
        jinja_config=jinja.jinja_config,
        host="0.0.0.0",  # noqa: S104 # nosec
        port=3000,
        uvicorn_log_level="warning",
    )


if __name__ == "__main__":
    asyncio.run(main())
