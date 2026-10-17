from __future__ import annotations


VALID_MESSAGE = (
    "REQ|MID=M-001|CASE=C-104|RESOURCE=WATER|QTY=20L|PEOPLE=18|"
    "LOC=GATE2|URGENT=Y"
)


def test_identical_retry_returns_original_result_without_duplicates(client, database):
    first = client.post("/api/messages", json={"raw_message": VALID_MESSAGE})
    second = client.post("/api/messages", json={"raw_message": VALID_MESSAGE})

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["response_message"] == first.json()["response_message"]

    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 1


def test_reusing_mid_with_changed_payload_is_a_conflict(client, database):
    client.post("/api/messages", json={"raw_message": VALID_MESSAGE})
    changed = VALID_MESSAGE.replace("QTY=20L", "QTY=30L")

    response = client.post("/api/messages", json={"raw_message": changed})

    assert response.status_code == 409
    assert response.json()["error_code"] == "MESSAGE_ID_REUSE"
    with database.connect() as connection:
        message = connection.execute(
            "SELECT raw_payload FROM messages WHERE message_id = 'M-001'"
        ).fetchone()
        case = connection.execute("SELECT quantity_litres FROM cases WHERE case_id = 'C-104'").fetchone()
        assert message["raw_payload"] == VALID_MESSAGE
        assert case["quantity_litres"] == 20.0


def test_valid_correction_reuses_case_with_a_new_mid(client, database):
    invalid = "REQ|MID=M-002|CASE=C-105|RESOURCE=WATER|QTY=twenty|PEOPLE=18|URGENT=Y"
    corrected = (
        "REQ|MID=M-004|CASE=C-105|RESOURCE=WATER|QTY=20L|PEOPLE=18|"
        "LOC=GATE2|URGENT=Y"
    )

    invalid_response = client.post("/api/messages", json={"raw_message": invalid})
    corrected_response = client.post("/api/messages", json={"raw_message": corrected})

    assert invalid_response.status_code == 422
    assert corrected_response.status_code == 201
    assert corrected_response.json()["case_id"] == "C-105"
    assert corrected_response.json()["case_status"] == "VALIDATED"

    with database.connect() as connection:
        case = connection.execute("SELECT * FROM cases WHERE case_id = 'C-105'").fetchone()
        assert case["status"] == "VALIDATED"
        assert case["quantity_litres"] == 20.0
        assert case["location"] == "GATE2"
        assert connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 2
