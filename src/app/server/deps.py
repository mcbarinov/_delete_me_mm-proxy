from typing import Annotated, cast

from fastapi import Depends
from starlette.requests import Request

from app.core.core import Core


def get_core(request: Request) -> Core:
    return cast(Core, request.app.state.core)


CoreDep = Annotated[Core, Depends(get_core)]
