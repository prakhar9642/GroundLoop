PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN (
        'CORRECTION_REQUIRED',
        'VALIDATED',
        'ACTION_ASSIGNED',
        'CONFIRMED'
    )),
    resource TEXT,
    quantity_litres REAL,
    people INTEGER,
    location TEXT,
    urgent INTEGER,
    latest_ack_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    message_type TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    outcome TEXT NOT NULL,
    case_status TEXT NOT NULL,
    parsed_payload_json TEXT,
    errors_json TEXT,
    response_message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    message_id TEXT REFERENCES messages(message_id),
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    detail_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_case_id ON messages(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_case_id ON audit_events(case_id, id);
