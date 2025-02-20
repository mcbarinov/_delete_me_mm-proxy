from markupsafe import Markup
from mm_base1.jinja import CustomJinja

from app.app import App


def header_info(app: App) -> Markup:
    info = ""
    stats = app.main_service.calc_stats()
    info += f"<span title='all proxies'>{stats.all.all}</span> / "
    info += f"<span title='ok proxies'>{stats.all.ok}</span> / "
    info += f"<span title='live proxies'>{stats.all.live}</span>"
    return Markup(info)


custom_jinja = CustomJinja(header_info=header_info)
