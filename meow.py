from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import cappa
from cappa.web import web
from typing_extensions import Annotated


@dataclass
class Example:
    """I Am a Title.

    Longer Description.
    """

    positional_arg: str = "optional"
    boolean_flag: bool = False
    single_option: Annotated[int | None, cappa.Arg(short=True, help="A number")] = None
    multiple_option: Annotated[
        list[Literal["one", "two", "three"]],
        cappa.Arg(long=True, help="Pick one!"),
    ] = field(default_factory=list)


web(Example)
