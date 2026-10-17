"""HTTP input models and small application-level constants."""

from __future__ import annotations

from pydantic import BaseModel


class MessageSubmission(BaseModel):
    # Empty strings are passed to the protocol parser so they receive the
    # same 400 PROTOCOL_REJECTED response as other unidentifiable messages.
    raw_message: str


class HealthResponse(BaseModel):
    service: str
    status: str
