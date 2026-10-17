"""Strict parsing for the small GroundLoop wire protocol."""

from __future__ import annotations

import re
from dataclasses import dataclass


ALLOWED_REQUEST_FIELDS = frozenset({"MID", "CASE", "RESOURCE", "QTY", "PEOPLE", "LOC", "URGENT"})
MESSAGE_ID_PATTERN = re.compile(r"^M-[A-Z0-9]+$")
CASE_ID_PATTERN = re.compile(r"^C-[A-Z0-9]+$")


class ProtocolError(Exception):
    """A protocol failure that must not be associated with a case."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ParsedRequest:
    raw: str
    message_id: str
    case_id: str
    fields: dict[str, str]


def parse_request(raw: str) -> ParsedRequest:
    """Parse a REQ message without coercing or guessing field values.

    Missing business fields are left for the validator so that a message with
    safe ``MID`` and ``CASE`` identity can be persisted for correction.
    Protocol-shape failures, including unknown fields, are rejected here.
    """

    if not raw or not raw.strip():
        raise ProtocolError("PROTOCOL_REJECTED", "Message is empty")

    segments = raw.split("|")
    if not segments or segments[0] != "REQ":
        raise ProtocolError("PROTOCOL_REJECTED", "Message must start with REQ")

    fields: dict[str, str] = {}
    for segment in segments[1:]:
        if "=" not in segment:
            raise ProtocolError("MALFORMED_FIELD", f"Field is missing '=': {segment!r}")
        key, value = segment.split("=", 1)
        if key not in ALLOWED_REQUEST_FIELDS:
            raise ProtocolError("UNKNOWN_FIELD", f"Unknown field: {key or '<empty>'}")
        if key in fields:
            raise ProtocolError("DUPLICATE_FIELD", f"Field repeated: {key}")
        fields[key] = value

    message_id = fields.get("MID")
    case_id = fields.get("CASE")
    if not message_id or not MESSAGE_ID_PATTERN.fullmatch(message_id):
        raise ProtocolError("PROTOCOL_REJECTED", "MID must match M-<uppercase letters or digits>")
    if not case_id or not CASE_ID_PATTERN.fullmatch(case_id):
        raise ProtocolError("PROTOCOL_REJECTED", "CASE must match C-<uppercase letters or digits>")

    return ParsedRequest(raw=raw, message_id=message_id, case_id=case_id, fields=fields)
