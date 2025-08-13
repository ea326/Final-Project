# app/operations/__init__.py

from typing import List, Union
from fastapi import HTTPException
from app.schemas.calculation import CalculationType

Number = Union[int, float]

def add(a: Number, b: Number) -> Number:
    return a + b

def subtract(a: Number, b: Number) -> Number:
    return a - b

def multiply(a: Number, b: Number) -> Number:
    return a * b

def divide(a: Number, b: Number) -> float:
    # IMPORTANT: keep ValueError for unit tests
    if b == 0:
        raise ValueError("Cannot divide by zero!")
    return a / b

def power(a: Number, b: Number) -> Number:
    return a ** b

def mod(a: Number, b: Number) -> Number:
    # IMPORTANT: keep ValueError for unit tests
    if b == 0:
        raise ValueError("Cannot mod by zero!")
    # return int(a) % int(b)  # <- uncomment for strict integer mod
    return a % b

def compute(calc_type: CalculationType, inputs: List[Number]) -> float:
    """
    Higher-level compute used by the API. Accepts a calc type and list of inputs.
    - add/sub/mul/div: allow 2+ inputs (div checks zeros)
    - power/mod: exactly two inputs (a, b)
    Converts domain ValueError -> HTTPException for API ergonomics.
    """
    if len(inputs) < 2:
        raise HTTPException(status_code=400, detail="At least two inputs are required")

    a, *rest = inputs
    try:
        if calc_type == CalculationType.ADDITION:
            return float(sum(inputs))

        if calc_type == CalculationType.SUBTRACTION:
            total = a
            for x in rest:
                total -= x
            return float(total)

        if calc_type == CalculationType.MULTIPLICATION:
            total: float = 1.0
            for x in inputs:
                total *= x
            return float(total)

        if calc_type == CalculationType.DIVISION:
            total = float(a)
            for x in rest:
                total = divide(total, x)  # may raise ValueError
            return float(total)

        if calc_type == CalculationType.POWER:
            if len(inputs) != 2:
                raise ValueError("Power expects exactly two inputs")
            return float(power(inputs[0], inputs[1]))

        if calc_type == CalculationType.MOD:
            if len(inputs) != 2:
                raise ValueError("Mod expects exactly two inputs")
            return float(mod(inputs[0], inputs[1]))  # may raise ValueError

        raise ValueError("Unsupported operation")

    except ValueError as e:
        # Translate domain errors to HTTP errors for API callers
        raise HTTPException(status_code=400, detail=str(e)) from e

__all__ = ["add", "subtract", "multiply", "divide", "power", "mod", "compute"]
