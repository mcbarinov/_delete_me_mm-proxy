from typing import cast

from fastapi import Depends
from mm_base6 import BaseView
from starlette.requests import Request

from app.core.core import Core


def get_core(request: Request) -> Core:
    return cast(Core, request.app.state.core)


class View(BaseView):
    core: Core = Depends(get_core)
