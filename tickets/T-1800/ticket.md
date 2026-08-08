---
id: T-1800
title: SYS108 missing from _KNOWN_GATE_RULES (TestKnownGateRuleIds red on main)
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
- src/frob/gates/_waive.py
- tickets/T-1800/**
- tickets/T-1805/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1800/**
  reason: 'T-1800: own ticket dir + the follow-up ticket filed during this ticket''s
    own work'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1805/**
  reason: 'T-1800: own ticket dir + the follow-up ticket filed during this ticket''s
    own work'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
---
Found while working T-1539 (PERF012 registry-entry gap). tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known fails on main (confirmed pre-existing, unrelated to T-1539's PERF012 change): SYS108 is constructed at src/frob/strata/_selfconform.py:1421 but absent from _KNOWN_GATE_RULES in src/frob/gates/_waive.py. Same drift class as the PERF012 gap T-1539 fixes -- paste the missing entry per generated_gate_rule_ids()'s report.

## Done report

Added the missing SYS108 entry to _KNOWN_GATE_RULES (src/frob/gates/
_waive.py), matching the existing SYS10x style/comment.

Checked whether any OTHER rule is missing from the table, per the
coordinator's direction, rather than fixing just the one instance:
scanned every `rule="..."` literal under src/frob/**/*.py (not just
_rule_id_scan.py's own SCANNED_BASES) against the post-fix
_KNOWN_GATE_RULES set. Zero real gaps remain -- the only unmatched id
(TIERBDEMO001) is deliberately excluded by design (a synthetic,
never-a-real-rule id documented in src/frob/gates/_fix_engine_tier_b.py
and src/frob/gates/_rule_id_scan.py's own RETIRED_RULE_IDS-style
exclusion comment).

Root cause, not just the symptom: found and confirmed why this table is
maintained by hand with nothing catching drift automatically. A land-time
auto-sync mechanism exists (frob.app.ticket_runner._land_cmd.
_sync_gate_rules_for_land, T-1011) specifically to make a land that grows
_KNOWN_GATE_RULES auto-file the matching check-coverage.yaml row in the
same commit -- but its trigger condition diffs ONLY src/frob/gates/
__init__.py for the literal text "_KNOWN_GATE_RULES". The literal itself
was moved OUT of __init__.py into _waive.py by T-1072 (2026-07-28,
confirmed via `git log -S`); __init__.py now only imports and consumes
the name, neither of which changes when a new id is appended to the
frozenset in _waive.py. Since T-1072, this auto-sync has been silently
inert for the ordinary edit shape -- confirmed as the actual cause behind
BOTH gaps found this session (PERF012, T-1539; SYS108, T-1800: both
landed via a diff to _waive.py alone, so the intended same-commit
registry-row behavior never fired for either).

Filed T-1805 (real id assigned at land) to point the auto-sync
mechanism's diff at the file the literal actually lives in -- out of this
ticket's own scope (src/frob/gates/_waive.py only), not fixed here.

### Changed
```
 tickets/T-1800/ticket.md           | 19 +++++++++++++-
 tickets/T-1805/ticket.md | 54 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 72 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 573 warning(s), 726 waived
- error-findings: none (measured, zero errors)
