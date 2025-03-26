import asyncio

import uvloop
from mm_base6 import init_server
from mm_base6.server.uvicorn import serve_uvicorn

from app import settings
from app.core.core import Core
from app.server.jinja import custom_jinja

asyncio.set_event_loop(asyncio.new_event_loop())


async def main() -> None:
    core = await Core.init(settings.core_config)
    await core.startup()
    await asyncio.sleep(1)
    fastapi_app = init_server(core, settings.server_config, custom_jinja, settings.get_router())
    await serve_uvicorn(fastapi_app, host="0.0.0.0", port=3000, log_level="warning")  # noqa: S104 # nosec


if __name__ == "__main__":
    uvloop.run(main())
