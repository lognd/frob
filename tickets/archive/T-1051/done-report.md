## Done report

Closed the 7 "needle-architecture-blocked" taxonomy rows T-1047 could not
express with a fixed needle+literal-arg-position construct: python/
typescript container-dynamic-key call and computed-member access with a
non-constant key (identical `container[expr](...)` source shape in both
languages, one detector covers both rows per language), c/c++ array-index
function-pointer dispatch, c/c++ integer-cast-to-function-pointer, and c/c++
void*-backcast-to-function-pointer.

Added a NEW, separate registry (`RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS` in
src/frob/vet/_capability_registry.py) and a new SHAPE-based scanner
(`_structural_opaque_findings`/`_needle_construct_findings` in
src/frob/vet/_capability.py) wired into `_opaque_indirection_findings`
alongside the existing needle scan -- a second, disclosed-over-approximation
detector class (subscript_call / explicit_fnptr_cast_call /
named_type_cast_call) rather than trying to force the fixed-needle
architecture to express a non-literal SHAPE. `_subscript_key_looks_literal`
keeps a literal-keyed subscript call (the ordinary resolver's job per
T-0665's own literal/non-literal split) from double-firing.

Each closed row's litmus fixture in tests/test_vet.py::
TestOpaqueIndirectionGate kept its ORIGINAL name (test function names are
referenced as evidence by T-0666's own archived Done report and by
src/frob/vet/_evasion_coverage.py's _EVASION_LITMUS_MAP -- renaming them
first broke COV003 against T-0666's archived evidence, caught and reverted
during verification) but the body now asserts the finding FIRES instead of
asserting an empty result. Added one new no-regression fixture,
test_python_container_literal_key_call_not_addressed_by_structural_gate,
locking that a literal-keyed subscript call does NOT trip the new
structural gate.

The 6 structural resolver-level points-to rows (rust struct-update field
rebinding, rust macro_rules! expansion, c++ pointer-to-member, kotlin
destructuring declarations, kotlin default-parameter-bound callables,
kotlin operator-invoke) are LEFT HONESTLY OPEN, not force-closed. Direct
investigation during this ticket confirmed each needs real resolver
rearchitecture, not just an alias-table extension: e.g. even adding a
Rust struct-field alias table (mirroring C's _record_c_field_alias) would
not close the struct-update row on its own, because
_collect_rust_candidates only resolves a call_expression whose function is
a bare identifier/scoped_identifier -- (h.run)(...)'s function is a
parenthesized field_expression, a call-target SHAPE the candidate
collector does not walk at all. Filed T-1063 (renumbered at
land) tracking these 6 rows with the specific gap found for each; their
existing litmus fixtures in tests/test_vet.py are untouched (still lock
the honest non-resolution).

Verification: `frob check --ticket T-1051` across gates-fast/gates-native/
gates-security/lint/static is clean (0 errors) after two fix-forward passes
-- first pass caught a COV003 break from the test-rename mistake (reverted)
and an ARCH001 line-count violation on _opaque_indirection_findings
(fixed by extracting _needle_construct_findings). The 2 remaining PII012
findings in gates-security (src/frob/tickets/_leases.py:539,549) are
pre-existing, outside this ticket's scope (src/frob/vet/**,
src/frob/gates/_opaque.py, docs/design/registry/evasion.yaml,
tests/test_vet.py) -- that file is not touched by this ticket.

### Changed
```
 src/frob/vet/_capability.py          | 155 ++++++++++++---
 src/frob/vet/_capability_registry.py | 103 ++++++++++
 tests/test_vet.py                    | 361 +++++++++++++++++++----------------
 3 files changed, 428 insertions(+), 191 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_container_dynamic_key_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_container_literal_key_call_not_addressed_by_structural_gate` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_computed_member_non_constant_key_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_container_dynamic_key_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_array_nonconstant_index_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_integer_cast_to_function_pointer_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_void_star_backcast_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_cpp_array_runtime_index_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 1 error(s), 1938 warning(s), 384 waived
- error-findings: PII012@src/frob/tickets/_leases.py
