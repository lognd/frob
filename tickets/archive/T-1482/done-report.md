## Done report

Built the INV-030/refinement-monotonicity diff pass docs/strata/policy.md
disclosed as missing enforcing code.

find_policy_weakenings (src/frob/strata/_policy.py) diffs every pair of
CompiledPolicy whose node_ids are related by strict scope containment
(a component policy nested inside a broader trust/label policy, or one
trust/label threshold nested inside a laxer one) and flags a child
re-declaration that is strictly less restrictive than what the parent
already required for the same target atom, across confine_use,
at_call_require_arg, and mediate.

forbid_call/forbid_import were deliberately dropped from the diff after
an implementation mistake: an early version compared aggregate ident
sets per rule kind and flagged ANY child forbid_call/forbid_import
re-declaration that didn't literally re-list every parent ident, even
when the child's rule targeted a completely unrelated ident (adding a
NEW prohibition, not overriding an old one). Caught by a test
(test_no_finding_when_child_never_overlaps_parent_scope) before landing.
forbid_call/forbid_import are purely additive under the union-of-
applicable-policies enforcement model docs/strata/policy.md#compilation
already describes, so no child re-declaration can ever weaken them --
this is now documented explicitly in both the invariant spec
(invariants/INV-051.md) and docs/strata/policy.md, with a regression
test (test_forbid_call_never_flagged_even_when_child_narrows) locking
the non-finding in.

Minted a genuinely new invariant, INV-051, rather than reusing the
existing INV-030 marker already sitting on this paragraph in
docs/strata/policy.md -- INV-030's real spec (invariants/INV-030.md) is
already claimed by _resolve_trust_scope's own, unrelated property
(trust-scoped policies auto-cover new nodes at that level), evidenced by
tests already on main. Reusing that id for a different property would
have been a marker collision, not proof of anything.

Also fixed: docs/strata/policy.md's INV003/INV004 waivers on the
refinement-monotonicity paragraph, which existed specifically because no
enforcing code existed yet -- removed now that find_policy_weakenings
backs the claim.

Ticket scope on filing was wrong (src/frob/strata/_mutation_audit.py,
src/frob/strata/_native_staleness.py -- both unrelated may-capability/
native-staleness modules); rescoped to src/frob/strata/_policy.py and
tests/unit/strata/test_policy.py before implementing (frob ticket scope
--remove/--add, reason recorded in the scope_changes audit trail).

Disclosed cut: this pass is TIER-1 only (a pure diff function over
already-compiled CompiledPolicies) -- wiring it into a frob check gate
over the real design/ policies is left as a follow-up, out of this
ticket's scope.

### Changed
```
 tickets/T-1482/ticket.md | 45 ++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 42 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_confine_use_broadened_home_detected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_at_call_require_dropped_arg_detected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_mediate_swapped_mediator_detected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_no_finding_when_child_only_strengthens` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_no_finding_when_child_never_overlaps_parent_scope` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_forbid_call_never_flagged_even_when_child_narrows` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/strata-sys/src/frob/registry/_staleness.py
