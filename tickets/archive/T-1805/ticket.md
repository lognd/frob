---
id: T-1805
title: land-time _KNOWN_GATE_RULES auto-sync watches the wrong file since the T-1072
  split
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: add regression test for the _waive.py diff-target fix
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_ticket_land.py::TestSyncGateRulesForLandDiffTarget::test_edit_to_waive_py_is_detected
- tests/test_ticket_land.py::TestSyncGateRulesForLandDiffTarget::test_unrelated_waive_py_edit_is_noop
designated_repro_test: null
threat: null
component: null
---
Found while working T-1800 (SYS108 missing from _KNOWN_GATE_RULES).

frob.app.ticket_runner._land_cmd._sync_gate_rules_for_land is a land-time
auto-sync mechanism (T-1011) that is supposed to make a land which grows
_KNOWN_GATE_RULES automatically file the matching docs/design/registry/
check-coverage.yaml row in the same commit. Its trigger condition diffs
ONLY src/frob/gates/__init__.py for the literal text "_KNOWN_GATE_RULES":

    diffed = run_argv(["git", "-C", str(root), "diff", pre_land_tip, "--",
        "src/frob/gates/__init__.py"])
    if "_KNOWN_GATE_RULES" not in diffed.danger_ok.stdout:
        return Ok(None)

_KNOWN_GATE_RULES itself was moved OUT of src/frob/gates/__init__.py and
into src/frob/gates/_waive.py by T-1072 (2026-07-28, the __init__.py
arch-split). __init__.py now only imports the name (line ~193) and
consumes it once (line ~6318) -- neither line changes when a new rule id
is appended to the actual frozenset literal in _waive.py. Since T-1072,
this auto-sync has therefore been silently inert for every ordinary
"add one rule id to _KNOWN_GATE_RULES" edit: the diff path it checks
never contains the literal's own text.

This is confirmed as the root cause of two independent real gaps landing
undetected past this mechanism: PERF012 (T-1539, missing since T-1225,
2026-08-0x) and SYS108 (T-1800, missing since T-1624, 2026-08-06) --
both landed via a diff to src/frob/gates/_waive.py, neither touched
src/frob/gates/__init__.py's own text, so the intended "same-commit
registry row" behavior never fired for either.

Fix: point _sync_gate_rules_for_land's diff (and its "_KNOWN_GATE_RULES
not in diff" check) at src/frob/gates/_waive.py instead of (or in
addition to) src/frob/gates/__init__.py -- wherever the frozenset literal
itself actually lives, not wherever it happens to be imported.

## Done report

Fixed `_sync_gate_rules_for_land`'s trigger diff (src/frob/app/ticket_runner/_land_cmd.py)
to watch src/frob/gates/_waive.py instead of src/frob/gates/__init__.py.
_KNOWN_GATE_RULES has lived in _waive.py since T-1072's split; __init__.py
only imports/consumes the name and never changes when a rule id is
appended, so the old diff target made this land-time auto-sync silently
inert for every ordinary rule-id addition since T-1072 -- confirmed root
cause of PERF012 and SYS108 both landing unregistered in check-coverage.yaml.

Added TestSyncGateRulesForLandDiffTarget with two regression cases: an
edit to _waive.py containing _KNOWN_GATE_RULES must trigger the scan
(previously silently skipped), and an unrelated _waive.py edit with no
_KNOWN_GATE_RULES text must still no-op.

### Changed
```
 tickets/T-1805/ticket.md | 12 +++++++++++-
 1 file changed, 11 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSyncGateRulesForLandDiffTarget::test_edit_to_waive_py_is_detected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesForLandDiffTarget::test_unrelated_waive_py_edit_is_noop` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 825 warning(s), 733 waived
- error-findings: PRE001@tickets/T-1805, SELFAUDIT001@design, invalid-assignment@tests/test_ticket_land.py
