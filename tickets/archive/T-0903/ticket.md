---
id: T-0903
title: _KNOWN_GATE_RULES omits 7 real, currently-firing rule ids (PARSE001/TICK005/REG011/PII011/PII012/SYSWAIVE002/THREAT006)
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round 2 --
completing the full catalog after the first pass's partial coverage).

`frob.gates.known_gate_rule_ids()` / `_KNOWN_GATE_RULES` (src/frob/gates/__init__.py:904)
is the single frozenset every `frob:waive RULE reason="..."` directive's
validity (WAIVE002: "rule id can never match") is checked against, AND the
set `known_rule_ids` a strata `caught_by`/registry `handled_by` resolution
treats as a recognized, real rule id rather than an unresolved reference
(the function's own docstring: "for strata caught_by resolution to
recognize rule-id-shaped references ... instead of treating them as
unresolved by default").

Verified via direct `known_gate_rule_ids()` call plus a grep for every
`rule="..."` site that actually constructs a `Violation`: at least 7 real,
firing rule ids are MISSING from this frozenset, despite gates.py actively
emitting them today:

- `PARSE001` (src/frob/gates/_parse_failures.py) -- registered as an
  always-run process job in `_ALL_GATES`'s "parse_failures" entry, but
  absent from `_KNOWN_GATE_RULES`.
- `TICK005` (src/frob/gates/__init__.py:7352, `_tick005_merge_state_regression`,
  dispatched from `tickets_gate`).
- `REG011` (src/frob/gates/_registry_exhaustiveness.py:301/317, T-0680's
  out_of_scope-reason check, dispatched from `registry_gate`).
- `PII011`, `PII012` (src/frob/gates/_pii_structural.py:892/957, dispatched
  from `pii_structural_gate`).
- `SYSWAIVE002` (src/frob/strata/_contention.py:437).
- `THREAT006` (src/frob/strata/_threat.py:1477).

This is exactly the DEAD001-class omission T-0753 already fixed once
("This was a listing omission, not evidence DEAD001 was ever renamed or
removed" -- see `_KNOWN_GATE_RULES`'s own DEAD001 comment) -- but the same
listing-omission bug has recurred at least 6 more times since, for rules
added by later tickets that never circled back to add their own entry
here. Concretely: any `frob:waive PARSE001 reason="..."` (or TICK005/
REG011/PII011/PII012/SYSWAIVE002/THREAT006) written anywhere in the tree
today is silently flagged WAIVE002-ineffective ("the rule id can never
match anything") despite targeting a perfectly real, currently-firing
rule -- and a strata `caught_by`/registry `handled_by` claim naming any of
these ids is treated as an UNRESOLVED reference rather than a recognized
enforced control, which can silently understate a threat-model/compliance
disposition's real coverage.

Fix direction: add the 7 missing ids to `_KNOWN_GATE_RULES`. More
durably, per this ticket's own pattern-recognition: add a drift-lock test
(or a small script gate) that diffs `_KNOWN_GATE_RULES` against every
`rule="..."` string literal actually constructed inside `src/frob/gates/**`
and `src/frob/strata/**`'s Violation-building sites, failing loud on any
gap -- so this omission class cannot recur a third time.