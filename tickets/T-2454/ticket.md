---
id: T-2454
title: _KNOWN_GATE_RULES is a hand-maintained literal that serializes every gate-adding
  ticket
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_rule_id_scan.py
- src/frob/app/registry_runner.py
- tests/gates/test_rule_id_scan_branches.py
- tests/unit/test_app_runners_t0875_leaf_collision.py
- src/frob/gates/_wire.py
- tests/test_gates.py
- docs/design/registry/EXHAUSTIVENESS-GATE.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_rule_id_scan.py
  reason: GATERULE001/T-1956 close-time preflight both compare a scanned candidate
    against ONLY the hand-maintained _KNOWN_GATE_RULES literal, forcing every new-gate-adding
    ticket to edit src/frob/gates/_waive.py and collide on its scope lease; find_unregistered_rule_ids
    now unions in the already-existing generated_gate_rule_ids scan so a standard
    rule= construction is auto-recognized without a hand edit, and frob registry audit
    --sync-gate-rules reports the full generated set for auditability
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/registry_runner.py
  reason: GATERULE001/T-1956 close-time preflight both compare a scanned candidate
    against ONLY the hand-maintained _KNOWN_GATE_RULES literal, forcing every new-gate-adding
    ticket to edit src/frob/gates/_waive.py and collide on its scope lease; find_unregistered_rule_ids
    now unions in the already-existing generated_gate_rule_ids scan so a standard
    rule= construction is auto-recognized without a hand edit, and frob registry audit
    --sync-gate-rules reports the full generated set for auditability
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/gates/test_rule_id_scan_branches.py
  reason: GATERULE001/T-1956 close-time preflight both compare a scanned candidate
    against ONLY the hand-maintained _KNOWN_GATE_RULES literal, forcing every new-gate-adding
    ticket to edit src/frob/gates/_waive.py and collide on its scope lease; find_unregistered_rule_ids
    now unions in the already-existing generated_gate_rule_ids scan so a standard
    rule= construction is auto-recognized without a hand edit, and frob registry audit
    --sync-gate-rules reports the full generated set for auditability
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_app_runners_t0875_leaf_collision.py
  reason: GATERULE001/T-1956 close-time preflight both compare a scanned candidate
    against ONLY the hand-maintained _KNOWN_GATE_RULES literal, forcing every new-gate-adding
    ticket to edit src/frob/gates/_waive.py and collide on its scope lease; find_unregistered_rule_ids
    now unions in the already-existing generated_gate_rule_ids scan so a standard
    rule= construction is auto-recognized without a hand edit, and frob registry audit
    --sync-gate-rules reports the full generated set for auditability
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_wire.py
  reason: the actual diff-scoped WIRE001 case 2 (_wire001_rule_id_violations, T-1421/BUG002)
    fires the moment a tickets OWN diff constructs a new rule= literal, checking known_gate_rule_ids()
    directly -- the same hand-literal-only comparison the GATERULE001/T-1956 fix already
    addressed, and very likely the actual mechanism serializing the 4 deadlocked tickets
    since it fires diff-locally, same session
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gates.py
  reason: wire_gate/_wire001_rule_id_violations own test coverage lives here; adding
    a positive-control test for the T-2454 union fix
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: 'AFFECT001: registry_runner.run changed (T-2454 --sync-gate-rules audit
    line); update the REG010 doc section to mention the new generated-audit-list log
    line'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_new_standard_shape_rule_recognized_without_hand_registration
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_disclosed_gap_shape_still_requires_hand_registration
- tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_standard_shape_new_rule_not_flagged_without_hand_registration
- tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_shape_outside_scanned_bases_still_flagged
- tests/unit/test_app_runners_t0875_leaf_collision.py::TestRegistryRunnerRun::test_sync_gate_rules_logs_the_full_generated_rule_id_set
designated_repro_test: null
acceptance:
- text: Given two tickets each adding a different new gate rule, when both are worked,
    then neither needs to edit a file the other holds, and both can land independently.
  evidence:
  - tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_new_standard_shape_rule_recognized_without_hand_registration
  - tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_disclosed_gap_shape_still_requires_hand_registration
  - tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_standard_shape_new_rule_not_flagged_without_hand_registration
  - tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_shape_outside_scanned_bases_still_flagged
- text: Given a gate constructing a rule id declared nowhere, when the registry check
    runs, then it is still reported, proving the check was not removed along with
    the bottleneck.
  evidence:
  - tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_new_standard_shape_rule_recognized_without_hand_registration
  - tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_disclosed_gap_shape_still_requires_hand_registration
  - tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_standard_shape_new_rule_not_flagged_without_hand_registration
  - tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_shape_outside_scanned_bases_still_flagged
- text: Given the derived registry, when a maintainer asks for the complete list of
    registered rule ids, then it is obtainable in one place as a generated artifact
    rather than a hand-kept literal.
  evidence:
  - tests/unit/test_app_runners_t0875_leaf_collision.py::TestRegistryRunnerRun::test_sync_gate_rules_logs_the_full_generated_rule_id_set
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: 9dd7c705da5646d21e36f3b184a30d329eef1312
---
`_KNOWN_GATE_RULES` in `src/frob/gates/_waive.py` is a hand-maintained
frozenset literal that EVERY ticket adding a gate rule must edit. It is
therefore a single-file serialization point for an entire class of
otherwise scope-disjoint work -- structurally the same defect as
CHANGELOG.md (T-2445).

MEASURED COST TODAY: four tickets deadlocked behind one small
registration ticket.

    T-2388  needed bare PORT001
    T-2435  needed GATESSCHEMA001
    T-2436  needed TESTRUNNERSCHEMA001
    T-2437  needed DUPSCHEMA001, GRAPHSCHEMA001

All four waited on T-2441, whose own land was itself stuck retrying
against an unrelated dirty root. Two agents polled the lease (one for
~15 minutes) and both correctly refused to force or steal it; one
retired at budget with three finished, tested, unlandable tickets. The
eventual fix was a human-directed cross-ticket courtesy registration
bundling all four ids into T-2441's commit -- which worked, but is a
coordination workaround, not a mechanism.

PROPOSED FIX (from the agent that hit it, and I agree): derive the
registry from each gate module's OWN declared rule ids -- each gate
module exports its rule-id constants, and the registry is built by
scanning `src/frob/gates/*` rather than hand-maintained in one literal.
A ticket adding a gate then touches only its own new module, and the
collision disappears entirely.

The stated cost is losing the single human-readable audit list of every
rule id. That is real but recoverable: emit the derived list as a
generated artifact (or a `frob` subcommand) so the auditability survives
without the write contention. Do not drop that property silently -- if
the derived approach cannot preserve it, say so and re-open the choice.

RELATED, AND SHOULD PROBABLY LAND FIRST: T-2448 notes that
`find_unregistered_rule_ids` (T-1937) already exists, is tested, and is
proven -- it is simply never run as a standing `frob check` gate, only
scope-limited at one ticket's own close/land time. Surfacing it
repo-wide would make registration gaps visible BEFORE they block a land,
which mitigates this bottleneck even if the derivation is never built.
That is the third instance today of the "detected but not surfaced"
pattern, after the inert CLI flags (T-2387) and the inert waivers
(T-2438).

Also note an audit gap found while measuring this: `CLAUDE001` at
`src/frob/app/check_runner.py:481` is unregistered in the live
`rule-bookkeeping` worktree (filed as T-2447), and four worktrees
(`gate-internals`, `land-integrity-series`, `reg-enforce`,
`t1893-t1908`) run a frob version predating the scanner and could not be
checked at all. The true unregistered count is therefore a LOWER BOUND,
not a measurement -- state it that way.

POSITIVE CONTROLS:
  - must-now-succeed: two tickets each adding a different new gate rule
    can both be worked and landed without either editing a file the
    other needs.
  - must-still-refuse: a gate constructing a rule id that is genuinely
    undeclared anywhere is still caught -- do not remove the check along
    with the bottleneck.
  - must-preserve-auditability: the complete list of registered rule ids
    remains obtainable in one place, generated rather than hand-kept.