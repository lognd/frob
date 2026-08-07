---
id: T-1050
title: 'vet/opaque: generalized container-subscript-call detector + rust/cpp/kotlin
  points-to alias tracking (T-1047 residual)'
state: dropped
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/gates/_opaque.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1047 closed 17 of the ~25 taxonomy runtime-opaque gaps T-0666 found (15
new RUNTIME_OPAQUE_CONSTRUCTS needle-based detector entries across
python/typescript/c-cpp/rust/kotlin, plus 2 new rust OPAQUE_SOURCE_INVISIBLE
excuse entries for the extern-FFI-symbol and proc-macro-expansion rows).
The remaining gaps genuinely need MORE than a fixed-substring needle match
-- a generic "container subscript followed by a call" shape
(`handlers[key](x)`, `cp[key](x)`), or a real cast-expression / points-to
analysis (C integer-to-function-pointer cast, C void*-backcast,
C/C++ array-index-into-function-pointer-table with a runtime index) --
which `_opaque_indirection_findings`'s current architecture (a byte-level
needle scan with an optional single-literal-argument check, T-0665) cannot
express without either a full expression grammar or an unacceptable false
positive rate on ordinary bracket/call syntax. Extending that architecture
is real design work, not a registry-entry addition, so it is scoped
separately here rather than forced into T-1047's needle-table shape.

Remaining runtime-opaque taxonomy rows still with NO detector/excuse
(litmus fixtures already lock the current honest non-firing behavior in
tests/test_vet.py::TestOpaqueIndirectionGate, `_not_addressed` suffix):
- python: container-dynamic-key (`handlers[key](x)`)
- typescript: computed-member-non-constant-key (`cp[key](x)`),
  container-dynamic-key (`handlers[key](x)`)
- c: array-nonconstant-index, integer-cast-to-function-pointer,
  void-star-backcast
- cpp: array-runtime-index

Also carried forward from T-0666/T-1047, structural resolver gaps in the
ORDINARY (non-opaque-gate) resolver, `frob.vet._capability.scan_file_
capabilities` and friends -- litmus fixtures already lock these too:
- rust: struct-field points-to (struct-update field rebinding never
  resolves through a later call) --
  `test_struct_update_field_rebind_not_detected`
- rust: `macro_rules!` expansion (no macro-expansion-aware resolution
  exists for rust at all) --
  `test_macro_rules_expansion_emitting_fixed_call_not_detected`
- cpp: pointer-to-member alias tracking (`&Ops::run` / `.*`/`->*`
  dereference has no alias tracking) --
  `test_member_function_pointer_bound_to_named_member_not_detected`
- kotlin: destructuring-declaration alias tracking --
  `test_destructuring_declaration_not_detected`
- kotlin: default-parameter-forwarding alias tracking --
  `test_default_parameter_forwarding_callable_not_detected`
- kotlin: operator `fun invoke` / receiver-instance points-to --
  `test_operator_fun_invoke_making_object_directly_callable_not_detected`

Each needs either: (a) a generalized "subscript-then-call" detector shape
added to `_opaque_indirection_findings` (a new construct kind beyond the
current needle+literal-arg-index model), or (b) real points-to/alias
tracking added to the per-language ordinary resolvers (mirrors C's
existing `_record_c_field_alias` for the rust/cpp/kotlin cases). Until
closed, T-0339's acceptance criterion [1] ("given any RUNTIME-resolved
indirection... FAILS CLOSED") does not fully hold -- these 7 opaque-gate
rows and 6 structural-resolver rows are the reason T-0339 was NOT closed
alongside T-1047.

## Failure log
- 2026-07-28 attempt 1: duplicate/superseded: T-1051 (done) already implemented the generalized container-subscript-call + cast-then-call structural detector this ticket describes, and T-1063 (done) already closed the rust/cpp/kotlin points-to alias-tracking residual T-1050 also names; no undone work remains under this ticket's scope

## Drop reason
- 2026-07-28: superseded before start: T-1051 (done) implemented the exact generalized container-subscript-call/cast-then-call structural detector this ticket describes, and T-1063 (done) closed the rust/cpp/kotlin points-to residual it names; verified by the wave-17 vet agent, fail-logged 9526c858