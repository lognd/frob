---
id: T-3308
title: frob ticket new --json does not print JSON
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-018).

`frob ticket new --json` does not print a JSON object -- output is still the
human-readable line `created T-draft-xxxx: <title>` plus any warnings.
Scripts that call `frob ticket new` programmatically have to regex the id
out of human text despite passing --json. Compare `frob ticket show --json`
(src/frob/app/ticket_runner/_query.py:180, `ticket.model_dump_json`) which
DOES honor --json correctly -- `new`'s handler needs the same treatment.

WHAT TO BUILD: when `--json` is passed to `frob ticket new`, print a JSON
object (at minimum the new ticket id; consider echoing warnings as a
structured list rather than dropping them, since scripted callers may still
want to see them).

MUST-FIRE / MUST-STAY-QUIET: `frob ticket new --json --title ... --kind ...`
must produce valid, parseable JSON on stdout containing the created id;
without --json, output is unchanged.
