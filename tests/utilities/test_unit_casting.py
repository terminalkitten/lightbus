from datetime import datetime, timezone, date
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, Optional, List, Any, SupportsRound
from uuid import UUID

import pytest
from dataclasses import dataclass

from lightbus.transports.redis import redis_stream_id_subtract_one
from lightbus.utilities.casting import cast_to_signature, cast_to_hint
from lightbus.utilities.frozendict import frozendict

pytestmark = pytest.mark.unit


def test_cast_to_signature_simple():

    def fn(a: int, b: str, c):
        pass

    obj = object()
    casted = cast_to_signature(callable=fn, parameters={"a": "1", "b": 2, "c": obj})
    assert casted == {"a": 1, "b": "2", "c": obj}


def test_cast_to_signature_no_annotations():

    def fn(a, b, c):
        pass

    obj = object()
    casted = cast_to_signature(callable=fn, parameters={"a": "1", "b": 2, "c": obj})
    # Values untouched
    assert casted == {"a": "1", "b": 2, "c": obj}


class SimpleNamedTuple(NamedTuple):
    a: str
    b: int


@dataclass
class SimpleDataclass(object):
    a: str
    b: int


class ExampleEnum(Enum):
    foo: str = "a"
    bar: str = "b"


class ComplexNamedTuple(NamedTuple):
    val: SimpleNamedTuple


@dataclass
class ComplexDataclass(object):
    val: SimpleDataclass


@dataclass
class DataclassWithMethod(object):
    a: str
    b: int

    def bar(self):
        pass


class CustomClass(object):
    pass


class CustomClassWithMagicMethod(object):
    value: str = "123"

    @classmethod
    def __from_bus__(cls, data):
        o = cls()
        o.value = data["value"]
        return o


@pytest.mark.parametrize(
    "test_input,hint,expected",
    [
        (1, int, 1),
        ("1", int, 1),
        (1.23, float, 1.23),
        ("1.23", float, 1.23),
        (True, bool, True),
        ("1", bool, True),
        ("", bool, False),
        (None, int, None),
        ("a", str, "a"),
        (1, str, "1"),
        ("1.23", Decimal, Decimal("1.23")),
        ("(1+2j)", complex, complex("(1+2j)")),
        ({"a": 1}, frozendict, frozendict(a=1)),
        (
            "abf4ddeb-fb9c-44c5-b865-012ba7787469",
            UUID,
            UUID("abf4ddeb-fb9c-44c5-b865-012ba7787469"),
        ),
        ({"a": 1, "b": "2"}, SimpleNamedTuple, SimpleNamedTuple(a="1", b=2)),
        ({"a": 1, "b": "2"}, SimpleDataclass, SimpleDataclass(a="1", b=2)),
        ({"a": 1, "b": "2"}, DataclassWithMethod, DataclassWithMethod(a="1", b=2)),
        (
            {"val": {"a": 1, "b": "2"}},
            ComplexNamedTuple,
            ComplexNamedTuple(val=SimpleNamedTuple(a="1", b=2)),
        ),
        (
            {"val": {"a": 1, "b": "2"}},
            ComplexDataclass,
            ComplexDataclass(val=SimpleDataclass(a="1", b=2)),
        ),
        (
            "2018-06-05T10:48:12.792937+00:00",
            datetime,
            datetime(2018, 6, 5, 10, 48, 12, 792937, tzinfo=timezone.utc),
        ),
        ("2018-06-05", date, date(2018, 6, 5)),
        ("123", Any, "123"),
        ("a", int, "a"),
        ("123", Optional[int], 123),
        (None, Optional[int], None),
        # Custom classes not supported, so the hint is ignored
        ("a", CustomClass, "a"),
        (["1", 2], list, ["1", 2]),
        (["1", 2], List, ["1", 2]),
        (["1", 2], List[int], [1, 2]),
        (["1", 2], SupportsRound, ["1", 2]),
        ("a", ExampleEnum, ExampleEnum.foo),
        ("x", ExampleEnum, "x"),
    ],
    ids=[
        "int_same",
        "int_cast",
        "float_same",
        "float_cast",
        "bool_same",
        "bool_cast_true",
        "bool_cast_false",
        "none",
        "str_same",
        "str_cast",
        "decimal",
        "complex",
        "frozendict",
        "uuid",
        "nametuple",
        "dataclass",
        "dataclass_with_method",
        "complex_namedtuple",
        "complex_dataclass",
        "datetime",
        "date",
        "str_any",
        "str_int",
        "optional_int_present",
        "optional_int_none",
        "custom_class",
        "list_builtin",
        "list_generic_untyped",
        "list_generic_typed",
        "unsupported_generic",
        "enum",
        "enum_bad_value",
    ],
)
def test_cast_to_annotation(test_input, hint, expected):
    casted = cast_to_hint(value=test_input, hint=hint)
    assert casted == expected


def test_cast_to_annotation_custom_class_with_magic_method():
    casted = cast_to_hint(value={"value": "abc"}, hint=CustomClassWithMagicMethod)
    assert isinstance(casted, CustomClassWithMagicMethod)
    assert casted.value == "abc"
