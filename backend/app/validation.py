"""Deterministic business validation and canonical normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .protocol import ParsedRequest


SUPPORTED_RESOURCES = frozenset({"WATER"})
QUANTITY_PATTERN = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?L$")
PEOPLE_PATTERN = re.compile(r"^[1-9]\d*$")
LOCATION_PATTERN = re.compile(r"^[A-Z0-9_-]+$")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    field: str
    instruction: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "field": self.field,
            "instruction": self.instruction,
        }


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    normalized_payload: dict[str, Any] | None
    errors: list[ValidationIssue]


def validate_request(request: ParsedRequest) -> ValidationResult:
    fields = request.fields
    errors: list[ValidationIssue] = []

    resource = fields.get("RESOURCE", "")
    if not resource:
        errors.append(ValidationIssue("RESOURCE_REQUIRED", "RESOURCE", "Provide a supported resource"))
    elif resource not in SUPPORTED_RESOURCES:
        errors.append(ValidationIssue("RESOURCE_INVALID", "RESOURCE", "Use WATER"))

    quantity_litres: float | None = None
    quantity = fields.get("QTY", "")
    if not QUANTITY_PATTERN.fullmatch(quantity):
        errors.append(ValidationIssue("QTY_INVALID", "QTY", "Use a positive quantity with an L suffix, for example 20L"))
    else:
        parsed_quantity = float(quantity[:-1])
        if parsed_quantity <= 0:
            errors.append(ValidationIssue("QTY_INVALID", "QTY", "Use a positive quantity with an L suffix, for example 20L"))
        else:
            quantity_litres = parsed_quantity

    people: int | None = None
    people_value = fields.get("PEOPLE", "")
    if not PEOPLE_PATTERN.fullmatch(people_value):
        errors.append(ValidationIssue("PEOPLE_INVALID", "PEOPLE", "Use a positive whole number"))
    else:
        people = int(people_value)

    location = fields.get("LOC", "")
    if not location:
        errors.append(ValidationIssue("LOC_REQUIRED", "LOC", "Provide a location code, for example GATE2"))
    elif not LOCATION_PATTERN.fullmatch(location):
        errors.append(ValidationIssue("LOC_INVALID", "LOC", "Use uppercase letters, digits, '_' or '-'"))

    urgent = fields.get("URGENT", "")
    if urgent not in {"Y", "N"}:
        errors.append(ValidationIssue("URGENT_INVALID", "URGENT", "Use Y or N"))

    if errors:
        return ValidationResult(valid=False, normalized_payload=None, errors=errors)

    return ValidationResult(
        valid=True,
        normalized_payload={
            "resource": resource,
            "quantity_litres": quantity_litres,
            "people": people,
            "location": location,
            "urgent": urgent == "Y",
        },
        errors=[],
    )
