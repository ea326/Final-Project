# tests/unit/test_calculator.py

import pytest
from typing import Union
from app.operations import add, subtract, multiply, divide, power, mod

Number = Union[int, float]

# ---------------------- add ----------------------
@pytest.mark.parametrize(
    "a, b, expected",
    [
        (2, 3, 5),
        (-2, -3, -5),
        (2.5, 3.5, 6.0),
        (-2.5, 3.5, 1.0),
        (0, 0, 0),
    ],
)
def test_add(a: Number, b: Number, expected: Number) -> None:
    assert add(a, b) == expected

# ------------------- subtract --------------------
@pytest.mark.parametrize(
    "a, b, expected",
    [
        (5, 3, 2),
        (-5, -3, -2),
        (5.5, 2.5, 3.0),
        (-5.5, -2.5, -3.0),
        (0, 0, 0),
    ],
)
def test_subtract(a: Number, b: Number, expected: Number) -> None:
    assert subtract(a, b) == expected

# ------------------- multiply --------------------
@pytest.mark.parametrize(
    "a, b, expected",
    [
        (2, 3, 6),
        (-2, 3, -6),
        (2.5, 4.0, 10.0),
        (-2.5, 4.0, -10.0),
        (0, 5, 0),
    ],
)
def test_multiply(a: Number, b: Number, expected: Number) -> None:
    assert multiply(a, b) == expected

# --------------------- divide --------------------
@pytest.mark.parametrize(
    "a, b, expected",
    [
        (6, 3, 2.0),
        (-6, 3, -2.0),
        (6.0, 3.0, 2.0),
        (-6.0, 3.0, -2.0),
        (0, 5, 0.0),
    ],
)
def test_divide(a: Number, b: Number, expected: float) -> None:
    assert divide(a, b) == expected

def test_divide_by_zero() -> None:
    with pytest.raises(ValueError) as excinfo:
        divide(6, 0)
    assert "Cannot divide by zero!" in str(excinfo.value)

# ---------------------- power --------------------
@pytest.mark.parametrize(
    "a, b, expected",
    [
        (2, 5, 32),
        (3, 0, 1),
        (4, 0.5, 2.0),
        (9, 0.5, 3.0),
    ],
)
def test_power(a: Number, b: Number, expected: Number) -> None:
    assert power(a, b) == expected

# ----------------------- mod ---------------------
@pytest.mark.parametrize(
    "a, b, expected",
    [
        (10, 3, 1),
        (14, 5, 4),
        (10.5, 2, 0.5),  # Python % works with floats
    ],
)
def test_mod(a: Number, b: Number, expected: Number) -> None:
    assert mod(a, b) == expected

def test_mod_by_zero() -> None:
    with pytest.raises(ValueError) as excinfo:
        mod(5, 0)
    assert "Cannot mod by zero!" in str(excinfo.value)
