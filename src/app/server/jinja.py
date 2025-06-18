from markupsafe import Markup
from mm_base6 import JinjaConfig

from app.core.types import AppCore


class AppJinjaConfig(JinjaConfig[AppCore]):
    filters = {}
    globals = {}
    header_info_new_line = False

    async def header(self) -> Markup:
        info = ""
        stats = await self.core.services.source.calc_stats()
        info += f"<span title='all proxies'>{stats.all.all}</span> / "
        info += f"<span title='ok proxies'>{stats.all.ok}</span> / "
        info += f"<span title='live proxies'>{stats.all.live}</span>"
        return Markup(info)  # noqa: S704 # nosec
