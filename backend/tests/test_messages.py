from __future__ import annotations


VALID_MESSAGE = (
    "REQ|MID=M-001|CASE=C-104|RESOURCE=WATER|QTY=20L|PEOPLE=18|"
    "LOC=GATE2|URGENT=Y"
)


def test_valid_request_is_normalized_and_persisted(client, database):
    response = client.post("/api/messages", json={"raw_message": VALID_MESSAGE})

    assert response.status_code == 201
    assert response.json() == {
        "duplicate": False,
        "message_id": "M-001",
        "case_id": "C-104",
        "message_outcome": "VALIDATED",
        "case_status": "VALIDATED",
        "normalized_payload": {
            "resource": "WATER",
            "quantity_litres": 20.0,
            "people": 18,
            "location": "GATE2",
            "urgent": True,
        },
        "response_message": "ACK|MID=M-001|CASE=C-104|STATUS=VALIDATED|RESULT=CASE_ACCEPTED",
    }

    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 1


def test_invalid_quantity_and_missing_location_are_actionable(client, database):
    response = client.post(
        "/api/messages",
        json={
            "raw_message": "REQ|MID=M-002|CASE=C-105|RESOURCE=WATER|QTY=twenty|PEOPLE=18|URGENT=Y"
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["message_outcome"] == "CORRECTION_REQUIRED"
    assert body["case_status"] == "CORRECTION_REQUIRED"
    assert [error["code"] for error in body["errors"]] == ["QTY_INVALID", "LOC_REQUIRED"]
    assert body["correction_message"] == (
        "CORR|MID=M-002|CASE=C-105|STATUS=CORRECTION_REQUIRED|ERRORS=QTY_INVALID,LOC_REQUIRED"
    )

    with database.connect() as connection:
        message = connection.execute(
            "SELECT parsed_payload_json, raw_payload FROM messages WHERE message_id = 'M-002'"
        ).fetchone()
        case = connection.execute("SELECT * FROM cases WHERE case_id = 'C-105'").fetchone()
        assert message["parsed_payload_json"] is None
        assert "QTY=twenty" in message["raw_payload"]
        assert case["status"] == "CORRECTION_REQUIRED"
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 1


def test_unknown_field_is_rejected_without_creating_case(client, database):
    response = client.post(
        "/api/messages",
        json={
            "raw_message": (
                "REQ|MID=M-003|CASE=C-106|RESOURCE=WATER|QTY=20L|PEOPLE=18|"
                "LOC=GATE2|URGENT=Y|COLOR=BLUE"
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "UNKNOWN_FIELD"
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_unidentifiable_protocol_failure_is_a_400_without_persistence(client, database):
    response = client.post("/api/messages", json={"raw_message": ""})

    assert response.status_code == 400
    assert response.json()["error_code"] == "PROTOCOL_REJECTED"
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_zero_quantity_requires_correction(client, database):
    response = client.post(
        "/api/messages",
        json={
            "raw_message": (
                "REQ|MID=M-005|CASE=C-107|RESOURCE=WATER|QTY=0.00L|PEOPLE=18|"
                "LOC=GATE2|URGENT=Y"
            )
        },
    )

    assert response.status_code == 422
    assert [error["code"] for error in response.json()["errors"]] == ["QTY_INVALID"]
    with database.connect() as connection:
        assert connection.execute("SELECT quantity_litres FROM cases WHERE case_id = 'C-107'").fetchone()[0] is None
