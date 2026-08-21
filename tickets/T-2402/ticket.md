---
id: T-2402
title: wire frob ticket body's AppConfig fields into _config_external.py (T-2392 follow-up)
state: dropped
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_config_external.py
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
T-2392 added `frob ticket body` (set_body, CLI parser, dispatch handler,
AppConfig fields ticket_body_append/ticket_body_append_file/
ticket_body_set/ticket_body_set_file/ticket_body_reason/
ticket_body_reason_file) but could NOT wire the argparse-Namespace-to-
AppConfig field copy in src/frob/app/_config_external.py, because that
file was held by T-2387's live in-progress lease for T-2392's entire
session.

Effect: `frob ticket body ...` parses at the argparse layer and dispatches
to `_body`, but every `ticket_body_*` field is silently dropped before
AppConfig(**d) is constructed (the exact T-0749/T-2387 bug class) --
so the verb does NOT actually work end-to-end via the real CLI yet, only
via a directly-constructed AppConfig (which is how T-2392's own CLI tests
exercise it).

FIX: once T-2387 lands and releases the lease, add:
- to `_STRING_FIELDS`: "ticket_body_append", "ticket_body_set",
  "ticket_body_reason"
- to `_PATH_FIELDS`: "ticket_body_append_file", "ticket_body_set_file",
  "ticket_body_reason_file"

Positive control: `frob ticket body <id> --append TEXT --reason TEXT` run
through the ACTUAL CLI (subprocess or `App.from_args`, not a hand-built
AppConfig) must show the body changed -- the same "test the real argv
parse path" shape T-2387's own Description names as the gap its sibling
defect's tests skipped.

## Drop reason
- 2026-08-18: superseded: T-2393 wired the _config_external.py fields for both T-2392 and T-2393 fields directly, since T-2387's lease released mid-session (absorbed by T-2393)
