---
id: T-4303
title: WIRE001 fires on every new direct-dispatch verb's --help-only argparse dest
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- src/frob/_cli_parsers/_core.py
- tests/gates_suite/test_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: 'T-4303: discharge the whereis WIRE001 waiver (follow_up=T-4303) now that
    the real exemption lands -- the waiver''s own job is done'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/gates_suite/test_wire.py
  reason: 'T-4303: new WIRE001 exemption tests for the bypass-verb fix live here'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: changelog.d/T-4299.md
  reason: 'T-4303: discharge live-tracker citation -- changelog.d/T-4299.md''s own
    historical narrative literally spells follow_up=T-4303, which live_tracker_citations
    reads as an unclosed waiver binding; must reword to close'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: CHANGELOG.md
  reason: 'T-4303: discharge live-tracker citation -- changelog.d/T-4299.md''s own
    historical narrative literally spells follow_up=T-4303, which live_tracker_citations
    reads as an unclosed waiver binding; must reword to close'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: changelog.d/T-4299.md
  reason: 'T-4303: both are land-owned (git commit refuses: ''CHANGELOG.md is land-owned
    (T-0731)'' / ''changelog.d/T-4299.md is land-owned'' -- neither can actually be
    edited from a worktree, so the LiveTrackerCited citation there is unfixable in-scope;
    filed as a new ticket instead'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: CHANGELOG.md
  reason: 'T-4303: both are land-owned (git commit refuses: ''CHANGELOG.md is land-owned
    (T-0731)'' / ''changelog.d/T-4299.md is land-owned'' -- neither can actually be
    edited from a worktree, so the LiveTrackerCited citation there is unfixable in-scope;
    filed as a new ticket instead'
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'T-4303: record close-blocked-by-T-4320 status'
  actor: logan
  at: '2026-09-08'
  old_length: 925
  new_length: 2323
evidence:
- tests/gates_suite/test_wire.py::TestWireGate::test_new_cli_dest_inside_appconfig_bypass_parser_func_is_not_flagged
- tests/gates_suite/test_wire.py::TestWireGate::test_new_cli_dest_outside_appconfig_bypass_parser_func_still_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while working T-4299 (frob whereis). Every direct-dispatch verb (bind/agent/worktree/sync-skills, now whereis) registers a --help-only argparse parser whose dests are NEVER read through AppConfig by design -- the actual invocation bypasses AppConfig entirely (frob.__main__._dispatch's raw argv[0] scan). WIRE001 has no way to know this and flags the first NEW dest such a verb ever adds in a diff (pre-existing dests on bind/agent/worktree never got flagged only because they were never touched by a later diff). Right now this needs a per-verb frob:waive WIRE001 (see src/frob/_cli_parsers/_core.py::_add_whereis_parser's waiver for T-4299). Consider either: a WIRE001 exemption for parsers registered only for --help discoverability on a direct-dispatch verb (some structural marker), or documenting this as the expected/permanent posture so a waiver here does not need a fabricated follow_up ticket every time.


## BLOCKER: close refused by LiveTrackerCited against a land-owned file

The fix (src/frob/gates/_wire.py, src/frob/_cli_parsers/_core.py,
tests/gates_suite/test_wire.py) is complete, tested (real fail-then-pass
repro confirmed via --check-repro), and clean under `frob check --ticket
T-4303` except the pre-existing SCOPE002/T-4310 defect and unrelated
pre-existing findings. `frob ticket close T-4303` refuses with
LiveTrackerCited: changelog.d/T-4299.md's own historical narrative (copied
verbatim from T-4299's Done report at land time) literally contains the
text "follow_up=T-4303", which the close/land preflight
(frob.tickets._live_tracker.live_tracker_citations) reads as an unresolved
waiver binding. Both changelog.d/T-4299.md and CHANGELOG.md (its generated
aggregate) are land-owned -- `git commit` on either is refused outright by
this repo's own commit hook (T-0731/T-2445), so no worktree can ever edit
them to re-point the citation. Filed T-4320 to track the root cause
(the citation scan does not distinguish a live directive from a historical
changelog quotation of one). Did NOT set FROB_LAND_INTERNAL to bypass the
land-owned guard -- that is `frob ticket land`'s own internal marker, not
an agent's escape hatch. T-4303 is left in-progress with its work complete
and committed on this worktree's branch, pending either T-4320's fix or a
deliberate human-approved override.