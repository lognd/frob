---
id: T-1063
title: 'vet/resolvers: close 6 structural points-to gaps (rust struct-update+macro_rules,
  cpp ptr-to-member, kotlin destructure/default-param/invoke)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/test_vet.py
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets-archive.md
  reason: fixing T-0666's own archived evidence, which pointed at the exact litmus
    test names this ticket renamed when it closed the gap
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_struct_update_field_rebind_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_destructuring_declaration_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_default_parameter_forwarding_callable_detected
designated_repro_test: null
threat: null
component: null
---
T-1051 closed the 7 needle-architecture-blocked taxonomy rows via a new
generalized structural detector (RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS,
_structural_opaque_findings in src/frob/vet/_capability.py) matching
subscript-then-call and cast-then-call SHAPES rather than fixed needles.

The 6 structural resolver-level points-to rows remain genuinely open,
confirmed by direct investigation during T-1051 (not just re-asserted):

- rust: struct-update field rebinding (`let h = Handlers { run: C::new,
  ..default }; (h.run)("sh");`). Even adding a field-alias table mirroring
  C's `_record_c_field_alias` would NOT close this row on its own: Rust's
  `_collect_rust_candidates` only resolves a `call_expression` whose
  `function` is an `identifier` or `scoped_identifier` -- `(h.run)(...)`'s
  function is a parenthesized `field_expression`, a call-target SHAPE the
  candidate collector does not walk at all. Closing this row needs BOTH a
  struct-field alias table AND field-expression call-target resolution in
  the collector -- confirmed as two separate gaps, not one.
- rust: `macro_rules!` expansion emitting a fixed call. No macro-expansion
  handling exists anywhere in the Rust resolver (no `macro_rule`/
  `macro_invocation` node is ever matched); closing this means expanding a
  macro body's tokens as if inlined at the invocation site, an AST
  transformation this resolver's plain-walk architecture does not support.
- c++: pointer-to-member (`auto p = &Ops::run; (obj.*p)(x);` / `->*`).
  Same two-gap shape as the rust struct-update row: no pointer-to-member
  alias tracking exists AND the C/C++ candidate collector has no handling
  for a `.*`/`->*` dereference as a call target.
- kotlin: destructuring declarations (`val (a, b) = Pair(::runCmd, 0)`).
  `_kt_property_name_and_value` only matches a single-name
  `variable_declaration` node; kotlin's `multi_variable_declaration` grammar
  shape is never visited.
- kotlin: default-parameter-bound callables (`fun call(cb: (String) -> Unit
  = ::runCmd)`). No default-value-of-a-parameter alias recording exists
  (unlike C++'s `_record_c_default_param_alias`); `_kt_build_var_alias_table`
  only walks `variable_declaration` nodes.
- kotlin: operator-invoke (`class Handler { operator fun invoke(x) = ... };
  val h = Handler(); h(x)`). Needs receiver-INSTANCE points-to (`val h =
  Handler()` -> a later bare `h(x)` call resolving through the class's
  `invoke` operator) -- no instance points-to of any kind exists in the
  kotlin resolver today.

Each row is still locked by its own honest non-firing/non-resolving litmus
fixture in tests/test_vet.py (unchanged by T-1051) -- see T-1051's own
scope for the exact test names. This ticket tracks the real resolver
rearchitecture (candidate-collector call-target-shape extension plus the
per-language alias/points-to table growth) each row needs; T-0339 stays
open against these 6 rows until this closes or each gets a reasoned
OPAQUE_SOURCE_INVISIBLE excuse instead, per T-1051's own Done report.