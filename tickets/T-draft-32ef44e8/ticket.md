---
id: T-draft-32ef44e8
title: 'WIRE002: 4 WIRE001 waivers name already-done tickets'
state: in-progress
kind: bug
origin: agent
created: '2026-09-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob
branch: dev
scope:
- src/frob/webapp/_websec_headers.py
- docs/modules/webapp-websec-headers.md
- tests/unit/test_webapp_websec_headers.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/testing/_dotnet_runner.py
  reason: T-5524 already in-progress and owns these two files' WIRE001 waiver repoint;
    narrowing this ticket to the remaining a11y_statement.py/_websec_headers.py waivers
    to avoid scope collision
  actor: logan
  at: '2026-09-25'
- op: remove
  glob: src/frob/testing/_unity_batchmode.py
  reason: T-5524 already in-progress and owns these two files' WIRE001 waiver repoint;
    narrowing this ticket to the remaining a11y_statement.py/_websec_headers.py waivers
    to avoid scope collision
  actor: logan
  at: '2026-09-25'
- op: remove
  glob: src/frob/webapp/_a11y_statement.py
  reason: T-5470 already owns _a11y_statement.py's WIRE002 fix live (CROSSTICKET001
    collision); dropping it from this ticket. Adding webapp-websec-headers.md since
    SCOPE002 flagged lint_response_headers's frob:doc target as out of scope.
  actor: logan
  at: '2026-09-25'
- op: add
  glob: docs/modules/webapp-websec-headers.md
  reason: T-5470 already owns _a11y_statement.py's WIRE002 fix live (CROSSTICKET001
    collision); dropping it from this ticket. Adding webapp-websec-headers.md since
    SCOPE002 flagged lint_response_headers's frob:doc target as out of scope.
  actor: logan
  at: '2026-09-25'
- op: add
  glob: tests/unit/test_webapp_websec_headers.py
  reason: 'SCOPE002: this ticket''s remaining scope (_websec_headers.py) covers symbols
    whose frob:tests target this file; adding it to close the coverage gap.'
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 36173008509 (dev 473cee7656). Reproduces on
ubuntu-latest and macos-latest.

FAILED tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo
unexpected WIRE002 finding(s): 4 `frob:waive WIRE001` comments name a ticket
that is already done, which WIRE002 now (correctly) flags as stale:

- src/frob/testing/_dotnet_runner.py:179 run_dotnet_tests -> names T-4516
- src/frob/testing/_unity_batchmode.py:224 run_unity_batchmode -> names T-4516
- src/frob/webapp/_a11y_statement.py:138 _locate_statement_page -> names T-5454
- src/frob/webapp/_websec_headers.py:408 lint_response_headers -> names T-5326

All four referenced tickets are already closed. Each waiver needs either a
real open follow-up ticket to bind to, or the underlying WIRE001 condition
needs to be actually fixed and the waiver comment removed.

Proposed fix: for each site, either resolve the WIRE001 condition directly,
or file a fresh open follow-up ticket and repoint the waiver at it.
