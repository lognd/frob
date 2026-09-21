---
id: T-4951
title: 'WIRE forbid call / forbid import: parsed and declared by the built-in analyzable
  pack, enforced by no gate, while its auto-injection warns on every design load'
state: done
kind: feature
origin: agent
created: '2026-09-19'
priority: high
parent: T-4665
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_forbid_rules_gate.py
- design/litmus/forbid_rules.strata
- tests/gates_suite/test_forbid_rules.py
- design/litmus/fixtures/forbid_rules/violation.py
- design/litmus/fixtures/forbid_rules/clean.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/litmus/fixtures/forbid_rules/violation.py
  reason: litmus module needs bound code fixtures for the forbid_rules_gate positive/negative
    controls
  actor: logan
  at: '2026-09-19'
- op: add
  glob: design/litmus/fixtures/forbid_rules/clean.py
  reason: litmus module needs bound code fixtures for the forbid_rules_gate positive/negative
    controls
  actor: logan
  at: '2026-09-19'
evidence:
- tests/gates_suite/test_forbid_rules.py::TestForbidRulesGateLitmus::test_litmus_planted_violation_fires
- tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect::test_mention_in_comment_does_not_fire
- tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect::test_no_bound_code_is_uncheckable_not_clean
- tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect::test_forbidden_call_under_analyzable_fires
designated_repro_test: null
acceptance:
- text: 'Given forbid call / forbid import are parsed at grammar_policy.rs:129-140
    into ForbidCall/ForbidImport (_ast.py:675,685) and declared by the built-in std.policy.analyzable
    pack (_packs.py:42-48) yet enforced nowhere -- _policy_weakening_gate.py:15 deliberately
    excludes them and no other gate reads them -- when this lands, then a litmus case
    whose bound source calls eval() under std.policy.analyzable produces a finding:
    a planted positive control that fails at HEAD c8f56ef10.'
  evidence:
  - tests/gates_suite/test_forbid_rules.py::TestForbidRulesGateLitmus::test_litmus_planted_violation_fires
- text: Given a guard fails by crying wolf, when source merely mentions a forbidden
    ident in a comment or string literal, then a test asserts no finding is produced.
  evidence:
  - tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect::test_mention_in_comment_does_not_fire
- text: Given a guard fails by failing open, when a node has no source bound to it,
    then that outcome is reported distinguishably and is not counted as a clean pass.
  evidence:
  - tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect::test_no_bound_code_is_uncheckable_not_clean
- text: Given _effects.py already scans the tree and T-4669 is making that scan cached,
    when this gate evaluates forbid rules, then it joins the existing capability scan
    rather than adding a second full-tree walk.
  evidence:
  - tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect::test_forbidden_call_under_analyzable_fires
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
WIRE leaf from the pessimistic keyword audit (scratchpad/STRATA-KEYWORDS.md),
under T-4678's decision: nothing is deleted, dormant constructs are wired.
The audit lists this separately from the keyword verdicts because it is a GATE
finding, not a keyword-usage finding. Story points: 3.
IMMEDIATELY DISPATCHABLE -- no blockers.

THE FINDING. `forbid call` / `forbid import` are parsed, constructed by a
BUILT-IN pack, and enforced by nobody.

- **Parsed:** strata-core/src/parse/grammar_policy.rs:129-140 ->
  `ForbidCall` / `ForbidImport` (src/frob/strata/_ast.py:675, :685).
- **Constructed:** src/frob/strata/_packs.py:42-48 -- the built-in
  `std.policy.analyzable` pack forbids `eval`, `exec`,
  `importlib.import_module`, `__import__`, `getattr`, `setattr`, `delattr`.
- **Enforced:** NOWHERE. Planner-verified at HEAD:
  src/frob/gates/_policy_weakening_gate.py:15 reads "Deliberately excludes
  `forbid_call`/`forbid_import` from consideration -- not this module's
  decision, `find_policy_weakenings` itself already never flags them
  (`_policy.py`'s `test_forbid_call_never_flagged_even_when_child_narrows`,
  T-1482 finding: both rule forms are purely additive under [refinement])".

WHY THAT EXCLUSION IS NOT THE SAME AS ENFORCEMENT. The weakening gate's job is
to catch a POLICY being loosened between parent and child; forbid rules are
purely additive under refinement, so excluding them from a WEAKENING check is
correct and is not the bug. The bug is that no OTHER gate ever checks the forbid
rules against actual source. A rule that cannot be weakened and is also never
evaluated is decoration.

THE SHARP PART, and its link to SF-11. The pack that the elaborator **warns
about on every single design load** -- `require_analyzable` at
src/frob/strata/_packs.py:96-102, SF-11's 570 occurrences across 45 land logs,
~12.7 per land -- declares rules that are never checked against any source file.
So today the warning is pure cost with **zero enforcement behind it**: frob
tells every agent, every run, that it is auto-injecting a mandatory base pack
whose rules do nothing.

That also changes T-4673 (SF-11, the log-once fix). T-4673 keeps the first
warning and suppresses the repeats, which is right either way -- but once this
leaf lands, the warning finally MEANS something, because auto-injecting the pack
will actually cause source to be checked. Record that in T-4673's done-report if
it lands first; the two tickets are scope-disjoint (_packs.py vs the new gate)
and can run in parallel.

WHAT TO BUILD
A gate that enforces `ForbidCall.idents` / `ForbidImport.idents` against the
source bound to each node, joined against the capability scan
src/frob/strata/_effects.py already runs -- per the audit's own recommendation,
and so this does NOT add a second full-tree scan (see T-4669, which is making
that scan cached; coordinate rather than duplicating).

Per memory/guard-design-lessons.md, the three ways this guard would fail:
exempting the normal case (a forbidden call reached through an alias or a
re-export), failing open (no source bound to the node -> silently zero), and
crying wolf (flagging the definition site or a string literal). Address all
three explicitly in the design, and make "no source bound" a distinguishable
outcome rather than a clean pass.

POSITIVE CONTROL (the test that fails today)
A litmus case whose node's bound source calls `eval(` while
`std.policy.analyzable` is in force, asserted to produce a finding. It fails at
HEAD -- the pack is auto-injected on every load and the call is never checked.
Per memory/positive-control-or-it-proves-nothing.md this planted finding is the
acceptance, not a zero from a clean run. Add the negative control too: source
that merely MENTIONS eval in a comment or string must not be flagged.