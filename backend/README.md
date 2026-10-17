# GroundLoop backend

This is the first implementation slice for **GroundLoop — From field signals to verified action.**
It implements the deterministic `REQ` parser, business validation, SQLite persistence,
correction responses, and duplicate-safe message processing.

## Run locally

From `backend/`:

```bash
python -m pip install -r requirements.txt
python -m pytest
uvicorn app.main:app --reload
```

The default database is `backend/data/groundloop.db`. Set `GROUNDLOOP_DB_PATH` to
use another SQLite file.

## Submit a message

```bash
curl -X POST http://127.0.0.1:8000/api/messages \
  -H 'Content-Type: application/json' \
  -d '{"raw_message":"REQ|MID=M-001|CASE=C-104|RESOURCE=WATER|QTY=20L|PEOPLE=18|LOC=GATE2|URGENT=Y"}'
```

The endpoint returns `201` for a newly validated request, `422` for an
identifiable request needing correction, `400` for a protocol rejection, and
`409` for message-ID reuse or an invalid case transition. Retrying the exact
same raw message returns the original result with `duplicate: true` and does
not create another case, message, or audit event.
