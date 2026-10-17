from __future__ import annotations

import pytest

from app.protocol import ProtocolError, parse_request


def test_parse_request_keeps_business_values_uncoerced():
    parsed = parse_request(
        "REQ|MID=M-001|CASE=C-104|RESOURCE=WATER|QTY=20L|PEOPLE=18|LOC=GATE2|URGENT=Y"
    )

    assert parsed.message_id == "M-001"
    assert parsed.case_id == "C-104"
    assert parsed.fields["QTY"] == "20L"


def test_unknown_field_is_a_protocol_rejection():
    with pytest.raises(ProtocolError) as raised:
        parse_request(
            "REQ|MID=M-003|CASE=C-106|RESOURCE=WATER|QTY=20L|PEOPLE=18|"
            "LOC=GATE2|URGENT=Y|COLOR=BLUE"
        )

    assert raised.value.code == "UNKNOWN_FIELD"


def test_missing_identity_is_not_safe_to_persist():
    with pytest.raises(ProtocolError) as raised:
        parse_request("REQ|CASE=C-104|RESOURCE=WATER|QTY=20L")

    assert raised.value.code == "PROTOCOL_REJECTED"
