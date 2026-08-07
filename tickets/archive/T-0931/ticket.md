---
id: T-0931
title: Reconcile duplicate '# frob:raises' directive convention (T-0688 vs T-0689)
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/modules/arch.md
- docs/modules/gates.md
- tests/unit/test_arch.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: T-0931 requires renaming the frob:raises call-site directive across its
    docs sections and its own tests to reconcile the collision, per ticket instructions
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: T-0931 requires renaming the frob:raises call-site directive across its
    docs sections and its own tests to reconcile the collision, per ticket instructions
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0931 requires renaming the frob:raises call-site directive across its
    docs sections and its own tests to reconcile the collision, per ticket instructions
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_gates.py
  reason: T-0931 requires renaming the frob:raises call-site directive across its
    docs sections and its own tests to reconcile the collision, per ticket instructions
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_parses_frob_raises_declaration_on_call_line
- tests/unit/test_arch.py::TestMayRaiseResolver::test_declared_raises_substitutes_for_opaque_boundary_call
- tests/unit/test_arch.py::TestMayRaiseResolver::test_declared_raises_empty_set_is_honored_not_treated_as_absent
- tests/test_gates.py::TestExhaustiveHandlingGate::test_declared_frob_raises_directive_discharges_exhaust002
designated_repro_test: null
threat: null
component: null
---
T-0688 (this worktree) introduces a '# frob:raises <ExceptionType>' comment directive placed directly ABOVE a function's def, declaring function-wide intentional exception propagation (consumed by frob.gates._exhaustive_handling's EXHAUST002 check). T-0689, landed concurrently on main while this ticket was in flight, introduces a same-named '# frob:raises A, B' directive but SAME-LINE on a call site, parsed into NormalizedCall.declared_raises (a per-call-site declaration, different grammar/scope/consumer). Both use the literal verb text 'frob:raises' with different placement rules and different semantics -- this will collide/confuse at land time (a human or tool reading '# frob:raises X' cannot tell which convention applies without checking placement). Needs reconciling before both land together: rename one convention (e.g. T-0688's function-level directive to something like '# frob:propagates <Type>') or unify the grammar. Filed instead of silently deciding unilaterally, since T-0689 owns src/frob/arch/_mayraise.py and its own call-site convention outside this ticket's declared scope.