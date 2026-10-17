"""Transactional message processing for the GroundLoop backend core."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .database import Database
from .protocol import ParsedRequest, ProtocolError, parse_request
from .validation import ValidationIssue, ValidationResult, validate_request


VALIDATED = "VALIDATED"
CORRECTION_REQUIRED = "CORRECTION_REQUIRED"


class MessageIdReuseError(Exception):
    """A MID was submitted with a different payload."""


class InvalidStateError(Exception):
    """A recognized message cannot be applied to the current case state."""


@dataclass(frozen=True)
class SubmissionResult:
    status_code: int
    body: dict[str, Any]


class GroundLoopService:
    def __init__(self, database: Database):
        self.database = database

    def submit_message(self, raw_message: str) -> SubmissionResult:
        parsed = parse_request(raw_message)
        validation = validate_request(parsed)
        payload_hash = hashlib.sha256(raw_message.encode("utf-8")).hexdigest()

        with self.database.transaction() as connection:
            existing_message = connection.execute(
                "SELECT * FROM messages WHERE message_id = ?",
                (parsed.message_id,),
            ).fetchone()
            if existing_message is not None:
                if existing_message["payload_hash"] == payload_hash:
                    return SubmissionResult(status_code=200, body=self._duplicate_body(existing_message))
                raise MessageIdReuseError(parsed.message_id)

            if validation.valid:
                body = self._store_valid_message(connection, parsed, validation)
                return SubmissionResult(status_code=201, body=body)

            body = self._store_invalid_message(connection, parsed, validation)
            return SubmissionResult(status_code=422, body=body)

    def _store_valid_message(
        self,
        connection: sqlite3.Connection,
        parsed: ParsedRequest,
        validation: ValidationResult,
    ) -> dict[str, Any]:
        assert validation.normalized_payload is not None
        now = _timestamp()
        current_case = connection.execute(
            "SELECT * FROM cases WHERE case_id = ?",
            (parsed.case_id,),
        ).fetchone()
        previous_status: str | None = None

        if current_case is None:
            connection.execute(
                """
                INSERT INTO cases (
                    case_id, status, resource, quantity_litres, people, location,
                    urgent, latest_ack_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    parsed.case_id,
                    VALIDATED,
                    validation.normalized_payload["resource"],
                    validation.normalized_payload["quantity_litres"],
                    validation.normalized_payload["people"],
                    validation.normalized_payload["location"],
                    int(validation.normalized_payload["urgent"]),
                    now,
                    now,
                ),
            )
        else:
            previous_status = current_case["status"]
            if previous_status != CORRECTION_REQUIRED:
                raise InvalidStateError(
                    f"Case {parsed.case_id} is {previous_status}; a new REQ is only allowed for correction"
                )
            connection.execute(
                """
                UPDATE cases
                SET status = ?, resource = ?, quantity_litres = ?, people = ?,
                    location = ?, urgent = ?, updated_at = ?
                WHERE case_id = ?
                """,
                (
                    VALIDATED,
                    validation.normalized_payload["resource"],
                    validation.normalized_payload["quantity_litres"],
                    validation.normalized_payload["people"],
                    validation.normalized_payload["location"],
                    int(validation.normalized_payload["urgent"]),
                    now,
                    parsed.case_id,
                ),
            )

        response_message = (
            f"ACK|MID={parsed.message_id}|CASE={parsed.case_id}|"
            "STATUS=VALIDATED|RESULT=CASE_ACCEPTED"
        )
        normalized_json = _json(validation.normalized_payload)
        connection.execute(
            """
            INSERT INTO messages (
                message_id, case_id, message_type, raw_payload, payload_hash,
                outcome, case_status, parsed_payload_json, errors_json,
                response_message, created_at
            ) VALUES (?, ?, 'REQ', ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                parsed.message_id,
                parsed.case_id,
                parsed.raw,
                hashlib.sha256(parsed.raw.encode("utf-8")).hexdigest(),
                VALIDATED,
                VALIDATED,
                normalized_json,
                response_message,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO audit_events (
                case_id, message_id, event_type, from_status, to_status,
                detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parsed.case_id,
                parsed.message_id,
                "CASE_VALIDATED",
                previous_status,
                VALIDATED,
                _json({"response_message": response_message}),
                now,
            ),
        )
        return {
            "duplicate": False,
            "message_id": parsed.message_id,
            "case_id": parsed.case_id,
            "message_outcome": VALIDATED,
            "case_status": VALIDATED,
            "normalized_payload": validation.normalized_payload,
            "response_message": response_message,
        }

    def _store_invalid_message(
        self,
        connection: sqlite3.Connection,
        parsed: ParsedRequest,
        validation: ValidationResult,
    ) -> dict[str, Any]:
        now = _timestamp()
        current_case = connection.execute(
            "SELECT * FROM cases WHERE case_id = ?",
            (parsed.case_id,),
        ).fetchone()
        previous_status: str | None = None
        if current_case is None:
            connection.execute(
                """
                INSERT INTO cases (
                    case_id, status, resource, quantity_litres, people, location,
                    urgent, latest_ack_message, created_at, updated_at
                ) VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (parsed.case_id, CORRECTION_REQUIRED, now, now),
            )
        else:
            previous_status = current_case["status"]
            if previous_status in {"ACTION_ASSIGNED", "CONFIRMED"}:
                raise InvalidStateError(
                    f"Case {parsed.case_id} is {previous_status}; it cannot return to correction"
                )
            connection.execute(
                "UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?",
                (CORRECTION_REQUIRED, now, parsed.case_id),
            )

        errors = [issue.as_dict() for issue in validation.errors]
        error_codes = ",".join(issue["code"] for issue in errors)
        response_message = (
            f"CORR|MID={parsed.message_id}|CASE={parsed.case_id}|"
            f"STATUS=CORRECTION_REQUIRED|ERRORS={error_codes}"
        )
        connection.execute(
            """
            INSERT INTO messages (
                message_id, case_id, message_type, raw_payload, payload_hash,
                outcome, case_status, parsed_payload_json, errors_json,
                response_message, created_at
            ) VALUES (?, ?, 'REQ', ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                parsed.message_id,
                parsed.case_id,
                parsed.raw,
                hashlib.sha256(parsed.raw.encode("utf-8")).hexdigest(),
                CORRECTION_REQUIRED,
                CORRECTION_REQUIRED,
                _json(errors),
                response_message,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO audit_events (
                case_id, message_id, event_type, from_status, to_status,
                detail_json, created_at
            ) VALUES (?, ?, 'CORRECTION_REQUIRED', ?, ?, ?, ?)
            """,
            (
                parsed.case_id,
                parsed.message_id,
                previous_status,
                CORRECTION_REQUIRED,
                _json({"errors": errors, "response_message": response_message}),
                now,
            ),
        )
        return {
            "duplicate": False,
            "message_id": parsed.message_id,
            "case_id": parsed.case_id,
            "message_outcome": CORRECTION_REQUIRED,
            "case_status": CORRECTION_REQUIRED,
            "errors": errors,
            "correction_message": response_message,
        }

    @staticmethod
    def _duplicate_body(row: sqlite3.Row) -> dict[str, Any]:
        normalized_payload = (
            json.loads(row["parsed_payload_json"])
            if row["parsed_payload_json"] is not None
            else None
        )
        errors = json.loads(row["errors_json"]) if row["errors_json"] is not None else None
        body: dict[str, Any] = {
            "duplicate": True,
            "message_id": row["message_id"],
            "case_id": row["case_id"],
            "message_outcome": row["outcome"],
            "case_status": row["case_status"],
            "response_message": row["response_message"],
        }
        if normalized_payload is not None:
            body["normalized_payload"] = normalized_payload
        if errors is not None:
            body["errors"] = errors
            body["correction_message"] = row["response_message"]
        return body


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
