from __future__ import annotations

from dataclasses import dataclass

import cappa
from typing_extensions import Annotated

from tests.utils import backends, parse


def some_dep():
    return 5


@dataclass
class HasExecutableMethods:
    arg: int
    include_dep: bool = False

    @cappa.command
    def add(self, some_dep: Annotated[int, cappa.Dep(some_dep)]) -> int:
        if self.add:
            return self.arg + some_dep
        return self.arg

    @cappa.command
    def subtract(self, some_dep: Annotated[int, cappa.Dep(some_dep)]) -> int:
        if self.add:
            return self.arg - some_dep
        return self.arg


@backends
def test_add(backend):
    result = parse(HasExecutableMethods, "10", "add", backend=backend)
    assert result == 10

    result = parse(HasExecutableMethods, "10", "--include-dep", "add", backend=backend)
    assert result == 15


@backends
def test_subtract(backend):
    result = parse(HasExecutableMethods, "10", "subtract", backend=backend)
    assert result == 10

    result = parse(
        HasExecutableMethods, "10", "--include-dep", "subtract", backend=backend
    )
    assert result == 15
