from dataclasses import dataclass
from typing import Awaitable, Callable

StatFn = Callable[[int, str], Awaitable[tuple[str, str, int]]]


@dataclass(frozen=True)
class StatProvider:
    key: str
    title: str
    fn: StatFn


def get_default_providers():
    # Local imports to avoid circular imports at module load time
    from .battlestats import update_and_format_battlestats
    from .workingstats import update_and_format_workingstats

    return [
        StatProvider(
            key="bs",
            title="Battle Stats",
            fn=update_and_format_battlestats,
        ),
        StatProvider(
            key="ws",
            title="Working Stats",
            fn=update_and_format_workingstats,
        ),
    ]
