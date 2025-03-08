from markupsafe import Markup
from mm_base5 import CustomJinja

from app.core.core import Core


def header_info(core: Core) -> Markup:
    info = ""
    stats = core.source_service.calc_stats()
    info += f"<span title='all proxies'>{stats.all.all}</span> / "
    info += f"<span title='ok proxies'>{stats.all.ok}</span> / "
    info += f"<span title='live proxies'>{stats.all.live}</span>"
    return Markup(info)  # nosec: B704


def footer_info(_core: Core) -> Markup:
    info = ""
    return Markup(info)  # nosec: B704


custom_jinja = CustomJinja(
    header_info=header_info,
    header_info_new_line=False,
    footer_info=footer_info,
)
