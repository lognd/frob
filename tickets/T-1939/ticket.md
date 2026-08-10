---
id: T-1939
title: 'No rule-level telemetry: cannot measure which of 293 gate rules ever fire'
state: done
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/telemetry/
- tests/unit/telemetry/**
- src/frob/check/_python.py
- docs/guides/agentic-time-profiling.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/telemetry/**
  reason: tests for the new package belong in the ticket's scope; check/_python.py
    is the single call site where the gates-stage GateReport is available to hook
    rule-counts emission into
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/check/_python.py
  reason: tests for the new package belong in the ticket's scope; check/_python.py
    is the single call site where the gates-stage GateReport is available to hook
    rule-counts emission into
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: new module's frob:doc anchors live in this existing telemetry-docs page
    (added a new section rather than a new orphan doc file)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: the new frob.telemetry node requires design/frob.strata registration (SYS102),
    and adding the testsuite fs.read via-list entry for the new test file requires
    bumping its ratchet ceiling in the same diff (SELFAUDIT001/SYS111)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: the new frob.telemetry node requires design/frob.strata registration (SYS102),
    and adding the testsuite fs.read via-list entry for the new test file requires
    bumping its ratchet ceiling in the same diff (SELFAUDIT001/SYS111)
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_counts_kept_violations
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_waived_violations_still_count_as_fired
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_kept_and_waived_of_the_same_rule_combine
- tests/unit/telemetry/test_rule_counts.py::TestRuleFiringCounts::test_empty_report_produces_an_empty_map
- tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_appends_one_event_with_every_fired_rule
- tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_empty_report_appends_a_zero_rule_event
- tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts::test_respects_no_telemetry_opt_out
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
AUDIT FINDING (full gate audit, 2026-08-09).

The question "which of our 293 gate rules earn their keep?" cannot be
answered from recorded data. `.frob/telemetry.jsonl` (36,982 records,
8.6MB) has exactly two record shapes:

  ('args_head','duration_ms','exit','iso_ts','kind','subcommand','tree_hash')
  ('event','iso_ts','kind','ticket_id')

Zero records carry a rule dimension -- distinct rule ids in telemetry: 0.
So we record how long `frob check` TOOK and whether it PASSED, but never
which rules fired, how often, or how long each cost.

CONSEQUENCE: this audit had to proxy rule liveness by grepping the ticket
ledger for rule-id mentions. That proxy is biased in a way that matters --
it measures rules that caused ARGUMENT, not rules that caused WORK. A
rule that fires constantly and is fixed without comment looks identical
to a rule that never fires at all.

VALUE: rule-level firing counts would make three recurring decisions
mechanical instead of speculative -- retiring a rule that never fires,
finding the slowest rule when check time regresses, and identifying which
rules actually gate a given subsystem. It also gives the ratchet a real
denominator.

Prefer emitting this automatically from the existing gate-result path
(the findings already exist in memory at the end of every check; only the
write is missing) over adding a `frob gates stats` verb the operator must
know to run. Surfacing belongs where people already look.