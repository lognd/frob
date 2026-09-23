---
id: T-4993
title: 'Liveness fixtures for every registered SYS/SELFAUDIT rule: 79 defined rule
  ids, zero telemetry fires, no rule may stay registered without a fixture that makes
  it fire'
state: done
kind: invariant
origin: agent
created: '2026-09-19'
priority: high
parent: T-4804
tier: ticket
sprint: null
runs_last: false
milestone: 0.536.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_sys_rule_liveness.py
- design/litmus/sys_liveness.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates_suite/test_sys_rule_liveness.py::test_every_registered_rule_has_a_liveness_fixture
- tests/gates_suite/test_sys_rule_liveness.py::test_every_mapped_fixture_node_id_actually_exists_and_passes
- tests/gates_suite/test_sys_rule_liveness.py::test_sys_liveness_litmus_design_proves_sys204_end_to_end
- tests/gates_suite/test_sys_rule_liveness.py::test_liveness_mapping_has_no_stale_entries
designated_repro_test: null
acceptance:
- text: Given 79 rule ids of the SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM families
    are defined while telemetry records 614,294 fires across 82 rule ids with ZERO
    starting with SYS, when this lands, then each registered rule has a fixture that
    PLANTS its violation and asserts the rule reports it.
  evidence:
  - tests/gates_suite/test_sys_rule_liveness.py::test_every_mapped_fixture_node_id_actually_exists_and_passes
  - tests/gates_suite/test_sys_rule_liveness.py::test_sys_liveness_litmus_design_proves_sys204_end_to_end
- text: Given a rule may be registered later with no fixture, when the meta-test enumerates
    registered rule ids from the registration surface (never a grep), then it FAILS
    for any rule with no liveness fixture -- the positive control, which fails at
    HEAD c8f56ef10 with 79 rules and zero fixtures.
  evidence:
  - tests/gates_suite/test_sys_rule_liveness.py::test_every_registered_rule_has_a_liveness_fixture
- text: Given no rule is retired under T-4804's decision, when a rule cannot be made
    to fire at all, then that is recorded as a finding on T-4804 and the rule stays
    registered -- it is never deleted.
  evidence:
  - tests/gates_suite/test_sys_rule_liveness.py::test_liveness_mapping_has_no_stale_entries
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
Leaf under T-4804's decision (SF-01). Story points: 3.
IMMEDIATELY DISPATCHABLE -- no blockers.

THE DECISION THIS IMPLEMENTS: every existing SYS/SELFAUDIT rule gets a
positive-control fixture that makes it FIRE in CI before it may stay registered.
A rule that cannot be shown firing is not a rule, it is a claim. NO RULE IS
RETIRED -- a rule with no fixture yet is a rule needing a fixture, never a rule
to delete.

THE MEASUREMENT THAT FORCED IT (SF-01, scratchpad/STRATA-FRICTION.md):
- `.frob/telemetry.jsonl`, 31,459 rows: **614,294 rule fires across 82 distinct
  rule ids. Not one starts with SYS. SELFAUDIT001 appears exactly once.**
- For contrast: CPLACE002 124,184; CPLACE001 89,963; TICK014 88,050;
  DOCARCH001 59,362.
- **79 rule ids** of the SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM families are
  defined under src/frob/strata + src/frob/gates/_sys.py; zero appear in
  telemetry.
- Corroborating, from SF-19: the strata PII001-004 family has fired 0 times and
  is a permanent zero BY CONSTRUCTION, while the structural PII010/011/012
  fired 276 / 92 / 1,840 times. Two families, same three letters, opposite
  signal -- and only the fixtures would have told them apart.

WHY A FIXTURE AND NOT TELEMETRY. Instrumentation can only separate the four
readings of a zero (memory/silent-zero-is-the-dominant-bug-class.md: clean,
could-not-run, nothing-to-measure, matcher-never-fired). A planted finding the
rule MUST report is what proves the matcher works --
memory/positive-control-or-it-proves-nothing.md. And per
memory/catalogued-is-not-enforced.md, a rule being registered, documented and
shipped is not the same as a rule firing; this leaf makes registration itself
carry the evidence.

WHAT TO BUILD
1. Per registered SYS/SELFAUDIT rule, a fixture under `tests/gates_suite/` (and
   a `design/litmus/*.strata` model where the rule needs a design to fire
   against) that PLANTS the violation the rule exists to catch, asserting the
   rule reports it.
2. A **meta-test** that enumerates the registered rule ids and FAILS for any
   rule with no liveness fixture. This is the part that makes the property
   durable rather than a one-off sweep: a newly registered rule without a
   fixture fails CI.
3. Where a rule genuinely cannot be made to fire, that is a FINDING to record on
   T-4804, not a licence to delete it -- it means the rule as written cannot
   detect its own subject, which is exactly what SF-01 suspected and could not
   prove.

SEQUENCING. The rule-id enumeration must come from the registration surface, not
from a grep: a grep-derived list is the same lexical shortcut the owner's
token/grammar directive rules out, and it would silently miss rules registered
dynamically. If no single registration surface exists to enumerate, say so --
that is itself the finding, and it is the same shape the other planner's gate
kernel ticket (one registration interface from which the job list, known-rule
set, docs and check-coverage are all derived) exists to fix. Coordinate rather
than building a second enumerator.

POSITIVE CONTROL (the test that fails today)
The meta-test itself: it fails at HEAD c8f56ef10 because 79 defined rule ids
have zero fixtures between them. Its passing state is the deliverable. Per
memory/wrapper-exit-code-is-not-the-work.md the acceptance is the enumerated
rule-to-fixture mapping, not a green run.

SCOPE NOTE: deliberately scoped to tests/ and design/litmus/ only. This leaf
adds NO rule and changes NO rule's behaviour -- if a fixture reveals a rule is
broken, file that separately rather than fixing it under this id, so the
liveness sweep stays reviewable.