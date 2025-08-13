"""
Calculation Schemas Module (updated)

Adds power (a**b) and mod (a%b). Keeps your DB-oriented models intact and
adds a lightweight response model for compute-only endpoints.
"""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class CalculationType(str, Enum):
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"
    POWER = "power"      # NEW
    MOD = "mod"          # NEW


class CalculationBase(BaseModel):
    type: CalculationType = Field(
        ...,
        description="addition | subtraction | multiplication | division | power | mod",
        example="addition",
    )
    inputs: List[float] = Field(
        ...,
        description="List of numeric inputs for the calculation",
        example=[10.5, 3, 2],
        min_items=2,
    )

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        allowed = {e.value for e in CalculationType}
        if not isinstance(v, str) or v.lower() not in allowed:
            raise ValueError(f"Type must be one of: {', '.join(sorted(allowed))}")
        return v.lower()

    @field_validator("inputs", mode="before")
    @classmethod
    def check_inputs_is_list(cls, v):
        if not isinstance(v, list):
            raise ValueError("Input should be a valid list")
        return v

    @model_validator(mode="after")
    def validate_inputs(self) -> "CalculationBase":
        if len(self.inputs) < 2:
            raise ValueError("At least two numbers are required for calculation")
        if self.type == CalculationType.DIVISION:
            if any(x == 0 for x in self.inputs[1:]):
                raise ValueError("Cannot divide by zero")
        if self.type == CalculationType.MOD:
            if any(x == 0 for x in self.inputs[1:]):
                raise ValueError("Cannot mod by zero")
        if self.type in (CalculationType.POWER, CalculationType.MOD) and len(self.inputs) != 2:
            raise ValueError(f"{self.type.value} expects exactly two inputs")
        return self

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {"type": "addition", "inputs": [10.5, 3, 2]},
                {"type": "division", "inputs": [100, 2]},
                {"type": "power", "inputs": [2, 8]},
                {"type": "mod", "inputs": [14, 5]},
            ]
        },
    )


class CalculationCreate(CalculationBase):
    user_id: UUID = Field(..., description="Owner user UUID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "addition",
                "inputs": [10.5, 3, 2],
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
    )


class CalculationUpdate(BaseModel):
    inputs: Optional[List[float]] = Field(
        None, description="Updated inputs", example=[42, 7], min_items=2
    )

    @model_validator(mode="after")
    def validate_inputs(self) -> "CalculationUpdate":
        if self.inputs is not None and len(self.inputs) < 2:
            raise ValueError("At least two numbers are required for calculation")
        return self

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"inputs": [42, 7]}},
    )


class CalculationResponse(CalculationBase):
    id: UUID = Field(..., description="Calculation UUID")
    user_id: UUID = Field(..., description="Owner user UUID")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    result: float = Field(..., description="Computed result", example=15.5)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174999",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "addition",
                "inputs": [10.5, 3, 2],
                "result": 15.5,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
            }
        },
    )


class CalculationOnlyResponse(BaseModel):
    """Lightweight response for compute-only endpoint (no DB)."""
    result: float
