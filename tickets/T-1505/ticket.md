---
id: T-1505
title: 'vet/resolvers: close remaining 3 structural points-to gaps (rust macro_rules,
  cpp ptr-to-member, kotlin operator-invoke) -- T-1063 residue'
state: done
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_vet.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_capability_registry/_opaque.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/vet/**
  reason: narrowing the mega-glob src/frob/vet/** to the exact files this fix touches
    -- the structural-opaque registry (_opaque.py), its matcher (_capability_scan.py),
    and the litmus fixtures (test_vet.py) -- before starting, per the standing narrow-scope-before-start
    rule
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: narrowing the mega-glob src/frob/vet/** to the exact files this fix touches
    -- the structural-opaque registry (_opaque.py), its matcher (_capability_scan.py),
    and the litmus fixtures (test_vet.py) -- before starting, per the standing narrow-scope-before-start
    rule
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/vet/_capability_registry/_opaque.py
  reason: narrowing the mega-glob src/frob/vet/** to the exact files this fix touches
    -- the structural-opaque registry (_opaque.py), its matcher (_capability_scan.py),
    and the litmus fixtures (test_vet.py) -- before starting, per the standing narrow-scope-before-start
    rule
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_vet.py
  reason: narrowing the mega-glob src/frob/vet/** to the exact files this fix touches
    -- the structural-opaque registry (_opaque.py), its matcher (_capability_scan.py),
    and the litmus fixtures (test_vet.py) -- before starting, per the standing narrow-scope-before-start
    rule
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_vet.py::TestOpaqueIndirectionGate::test_cpp_pointer_to_member_call_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_macro_rules_dangerous_body_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_macro_rules_benign_body_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_kotlin_operator_invoke_instance_call_fires
designated_repro_test: null
threat: null
component: null
---
T-1063's Done report closed 3 of 6 tracked structural points-to gaps and
left 3 genuinely residual (its own body already documents why each is
architecturally deeper than a table addition, quoted from T-1063):

- rust: `macro_rules!` expansion emitting a fixed call. No macro-expansion
  handling exists anywhere in the Rust resolver; closing this means
  expanding a macro body's tokens as if inlined at the invocation site, an
  AST transformation the resolver's plain-walk architecture does not
  support.
- c++: pointer-to-member (`auto p = &Ops::run; (obj.*p)(x);` / `->*`). No
  pointer-to-member alias tracking exists AND the C/C++ candidate
  collector has no handling for a `.*`/`->*` dereference as a call target.
- kotlin: operator-invoke (`class Handler { operator fun invoke(x) = ... };
  val h = Handler(); h(x)`). Needs receiver-INSTANCE points-to -- no
  instance points-to of any kind exists in the kotlin resolver today.

Each row is locked by its own honest non-firing/non-resolving litmus
fixture in tests/test_vet.py (per T-1063's evidence). T-0339 stays open
against these 3 rows until this closes or each gets a reasoned
OPAQUE_SOURCE_INVISIBLE excuse instead.

Filed as the TICK011 remediation for T-1063 (drain-to-zero warning
burn-down, this ticket).