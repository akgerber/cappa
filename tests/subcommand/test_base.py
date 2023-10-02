from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import cappa
import pytest
from typing_extensions import Annotated

from tests.utils import backends, parse


@dataclass
class RequiredMissingOne:
    foo: Annotated[Union[str, None], cappa.Arg(long=True)] = None


@dataclass
class RequiredMissing:
    subcommand: Annotated[RequiredMissingOne, cappa.Subcommand]


@backends
def test_required_missing(backend):
    with pytest.raises(cappa.Exit) as e:
        parse(RequiredMissing, backend=backend)
    assert isinstance(e.value.message, str)
    assert (
        "the following arguments are required: {required-missing-one}"
        in e.value.message.lower()
    )


@dataclass
class RequiredProvidedOne:
    foo: Annotated[Union[str, None], cappa.Arg(long=True)] = None


@dataclass
class RequiredProvidedTwo:
    bar: Annotated[Union[str, None], cappa.Arg(long=True)] = None


@dataclass
class RequiredProvided:
    subcommand: Annotated[
        Union[RequiredProvidedOne, RequiredProvidedTwo], cappa.Subcommand()
    ]


@backends
def test_required_provided(backend):
    test = parse(
        RequiredProvided, "required-provided-one", "--foo", "foo", backend=backend
    )
    assert isinstance(test.subcommand, RequiredProvidedOne)
    assert test.subcommand.foo == "foo"

    test = parse(RequiredProvided, "required-provided-two", backend=backend)
    assert isinstance(test.subcommand, RequiredProvidedTwo)
    assert test.subcommand.bar is None

    test = parse(
        RequiredProvided, "required-provided-two", "--bar", "bar", backend=backend
    )
    assert isinstance(test.subcommand, RequiredProvidedTwo)
    assert test.subcommand.bar == "bar"


@cappa.command(name="one")
@dataclass
class NamedSubcommandOne:
    pass


@dataclass
class NamedSubcommand:
    subcommand: Annotated[NamedSubcommandOne, cappa.Subcommand()]


@backends
def test_named_subcommand(backend):
    test = parse(NamedSubcommand, "one", backend=backend)
    assert isinstance(test.subcommand, NamedSubcommandOne)
