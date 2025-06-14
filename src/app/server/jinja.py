from markupsafe import Markup
from mm_base6 import JinjaConfig

from app.core.types import AppCore


async def header_info(core: AppCore) -> Markup:
    info = ""
    stats = await core.services.source.calc_stats()
    info += f"<span title='all proxies'>{stats.all.all}</span> / "
    info += f"<span title='ok proxies'>{stats.all.ok}</span> / "
    info += f"<span title='live proxies'>{stats.all.live}</span>"
    return Markup(info)  # noqa: S704 # nosec


async def footer_info(_core: AppCore) -> Markup:
    info = ""
    return Markup(info)  # noqa: S704 # nosec


jinja_config = JinjaConfig(
    header_info=header_info,
    header_info_new_line=False,
    footer_info=footer_info,
)
