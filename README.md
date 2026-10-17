# GroundLoop
GroundLoop is a **bidirectional field-report-to-work-order bridge for campus facilities operations**. A student, guard, or maintenance worker can send a compact structured issue report; a coordinator can triage, assign, and resolve the resulting work order; and the reporter-facing acknowledgement always reflects the ticket's current state.

## MVP flow

```text
Field report → deterministic validation → work order → coordinator action → ACK
```

The demo includes a mobile-style field reporter and an operations command center on the same responsive screen.

### Message format

Valid messages use exactly these five pipe-separated segments, in this order:

```text
ISSUE|BUILDING=A|FLOOR=2|TYPE=LEAK|SEVERITY=HIGH
```

The parser is explicit and deterministic. It validates:

- `BUILDING`: one uppercase letter (`A`–`Z`)
- `FLOOR`: numeric floor `1`–`12`
- `TYPE`: `LEAK`, `ELECTRICAL`, `HVAC`, `PLUMBING`, `RESTROOM`, `DAMAGE`, or `LIGHTING`
- `SEVERITY`: `LOW`, `MEDIUM`, or `HIGH`
- no missing, duplicate, unknown, or malformed fields

This invalid message is rejected rather than guessed:

```text
ISSUE|BUILDING=A|FLOOR=second|TYPE=LEAK|SEVERITY=HIGH
```

Correction: use a numeric floor, such as `FLOOR=2`.

## Ticket lifecycle

Tickets use validated application-state transitions only:

```text
NEW → TRIAGED → ASSIGNED → RESOLVED
```

Assignment requires a maintenance team. The acknowledgement is derived from the live ticket record, for example:

```text
ACK|GL-001|STATUS=NEW
ACK|GL-001|STATUS=ASSIGNED|TEAM=MAINTENANCE
```

## Run locally

Requirements: Node.js 18+ and npm.

```bash
npm install
npm run dev
```

Open the local URL printed by Vite. For a production build:

```bash
npm run build
```

## Automated checks

```bash
npm test
npm run build
```

Tests cover valid normalization and original-message preservation, invalid floors, missing/duplicate/unsupported fields, valid lifecycle progression, invalid transitions, team requirements, and live acknowledgements.

## Live demo script

1. Click **Load sample** in the Field reporter panel.
2. Click **Validate & send report**. A new `GL-###` ticket appears at the top of Incoming work orders with status `NEW`.
3. Select **Mark as triaged** in the ticket details.
4. Select a maintenance team and click **Assign**. The acknowledgement changes to `STATUS=ASSIGNED|TEAM=...`.
5. Click **Mark resolved** and show the lifecycle and acknowledgement update to `RESOLVED`.
6. To demonstrate deterministic validation, enter the `FLOOR=second` example and submit it. The report stays out of the work-order list and explains the numeric correction required.

The dashboard includes three clearly labeled `DEMO DATA` tickets so the operations view is useful before the first report is submitted. Use **Reset demo** to restore them.

## Architecture and limitations

- React + TypeScript + Vite single-page application.
- `src/domain.ts` contains the parser, normalized report contract, ticket creation, transition rules, and acknowledgement generator.
- `src/App.tsx` contains the reporter and operations interfaces.
- Browser `localStorage` persists tickets across refreshes.
- Transport is simulated locally; no SMS, radio, external API, paid service, account, or real-world delivery is claimed.
