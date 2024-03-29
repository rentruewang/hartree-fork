from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

CONF = "conf"
DATA = "data"

T = TypeVar("T", contravariant=True)
R = TypeVar("R", covariant=True)


def exist_or_none(path: Path) -> Path | None:
    if not path.exists():
        return None
    return path


def skip_if_none(function: Callable[[T], R]) -> Callable[[T | None], R | None]:
    def _func(param: T | None) -> R | None:
        if param is None:
            return None

        return function(param)

    return _func
