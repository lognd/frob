---
id: T-1482
title: build policy refinement-monotonicity diff pass (INV-030)
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/policy.md
- src/frob/strata/_policy.py
- tests/unit/strata/test_policy.py
- invariants/INV-051.md
- src/frob/strata/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/strata/_mutation_audit.py
  reason: T-1482's actual work (INV-030 policy refinement-monotonicity diff pass)
    lives in _policy.py/_ast.py's PolicyDecl/CompiledPolicy machinery; _mutation_audit.py
    and _native_staleness.py are unrelated may-capability/native-staleness modules,
    apparently mis-scoped at filing time
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/strata/_native_staleness.py
  reason: T-1482's actual work (INV-030 policy refinement-monotonicity diff pass)
    lives in _policy.py/_ast.py's PolicyDecl/CompiledPolicy machinery; _mutation_audit.py
    and _native_staleness.py are unrelated may-capability/native-staleness modules,
    apparently mis-scoped at filing time
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_policy.py
  reason: T-1482's actual work (INV-030 policy refinement-monotonicity diff pass)
    lives in _policy.py/_ast.py's PolicyDecl/CompiledPolicy machinery; _mutation_audit.py
    and _native_staleness.py are unrelated may-capability/native-staleness modules,
    apparently mis-scoped at filing time
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_policy.py
  reason: T-1482's actual work (INV-030 policy refinement-monotonicity diff pass)
    lives in _policy.py/_ast.py's PolicyDecl/CompiledPolicy machinery; _mutation_audit.py
    and _native_staleness.py are unrelated may-capability/native-staleness modules,
    apparently mis-scoped at filing time
  actor: logan
  at: '2026-08-08'
- op: add
  glob: invariants/INV-051.md
  reason: new PolicyWeakening/find_policy_weakenings public symbols need an invariant
    spec file and __init__ export
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/__init__.py
  reason: new PolicyWeakening/find_policy_weakenings public symbols need an invariant
    spec file and __init__ export
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_confine_use_broadened_home_detected
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_at_call_require_dropped_arg_detected
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_mediate_swapped_mediator_detected
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_no_finding_when_child_only_strengthens
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_no_finding_when_child_never_overlaps_parent_scope
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_forbid_call_never_flagged_even_when_child_narrows
designated_repro_test: null
threat: null
component: null
---
docs/strata/policy.md documents that policy refinement is DESIGNED to be
monotonic downward (a child may only strengthen an inherited policy,
never weaken it), but compile_policies/_resolve_scope only resolve scope
membership -- there is no refinement-diff pass that compares a child's
policy set against its parent's and flags a weakening. The paragraph
currently states design intent, not an enforced guarantee (also
disclosed via a frob:waive INV003 reason on the same section). Build
the refinement-diff pass. Found while draining NEGEXIST001
(T-1477): the doc's absence-claim had no frob:until binding.