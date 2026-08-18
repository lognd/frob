---
id: T-2349
title: Recovered from T-2313's phantom TICK006 citation of T-2345
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2313's Done report claimed T-2345 was filed, but T-2345 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> Root cause found: `_parse_error_findings_from_json` (src/frob/app/
ticket_runner/_verify.py, OUT of this ticket's declared scope, filed
separately as T-2345) does `findings.add((d.get("code") or "", d.get(
"file") or ""))` for every error-severity diagnostic -- a diagnostic
missing BOTH fields becom

## Drop reason
- 2026-08-17: duplicate: TICK006 auto-filed this from a stale ledger read during T-2313's land -- T-2345 is real and queued (verified: tickets/T-2345/ticket.md, state=queued), created moments before this land ran. Same TICK006 false-positive pattern already seen once this session (T-2343, also dropped) -- possibly a land-time ledger-staleness bug worth its own ticket if it recurs a third time
