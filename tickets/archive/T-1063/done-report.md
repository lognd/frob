## Done report

Closed 3 of the 6 tracked structural points-to gaps; the other 3 are
genuinely residual, not attempted-and-abandoned (follow-up filed as
T-1505, renumbers at land).

Closed:
1. rust struct-update field rebinding: added `_record_rust_field_alias` /
   `_build_rust_field_alias_table` (file-wide field-name-keyed table,
   mirrors C's `_record_c_field_alias`) plus a new parenthesized
   field-expression call-target shape in `_collect_rust_candidates`.
2. kotlin destructuring declarations: added `_record_kt_destructure_alias`
   / `_kt_destructure_value_elements` (positional binding of each
   `multi_variable_declaration` element to its RHS call-argument list,
   mirrors rust's tuple-destructure alias table).
3. kotlin default-parameter-bound callables: added
   `_record_kt_param_default_aliases`. Kotlin's grammar hangs a
   parameter's default value as a SIBLING of the `parameter` node inside
   `function_value_parameters` (not a child of `parameter` itself, unlike
   C++'s `optional_parameter_declaration`) -- confirmed via direct AST
   inspection, so the C++ mirror's single-node shape does not apply
   as-is; implemented as a sibling-list walk instead.

Each closure flips its litmus assertion in tests/test_vet.py (renamed
`_not_detected` -> `_detected` per the ticket's own convention) and its
_EVASION_LITMUS_MAP entry in src/frob/vet/_evasion_coverage.py. T-0666's
own archived evidence (tickets-archive.md) pointed at the exact old test
names these renames touched, so its evidence lines were updated too
(scope extended to tickets-archive.md, closure-warned but not required).

Honestly residual (not closed, ticket's own body already documents why
each is architecturally deeper than a table addition):

4. rust `macro_rules!` expansion emitting a fixed call: needs an AST
   transformation (macro-body token substitution at the invocation site)
   this resolver's plain-walk architecture does not support at all -- no
   `macro_rule`/`macro_invocation` node is matched anywhere today. Not a
   table-extension; a genuine capability the resolver lacks.
5. c++ pointer-to-member (`&Ops::run` / `.*`/`->*`): investigated the
   fixture's own parse directly -- `(Ops::*p)("sh")` is not standard C++
   member-pointer-call syntax (real syntax is `(obj.*p)(x)`), and
   tree-sitter-cpp parses it as a `qualified_identifier` wrapping a
   `pointer_type_declarator`, an ambiguous/degenerate parse shape with no
   clean call-target node to hang an alias lookup off. Closing this
   properly needs the REAL `.*`/`->*` field-expression-of-pointer shape
   handled, which the fixture as written does not exercise -- flagged
   rather than forced through a fixture-specific special case.
6. kotlin operator `fun invoke` / receiver-instance points-to: needs
   instance-level points-to (`val h = Handler()` -> a later bare `h(x)`
   resolving through `Handler`'s `invoke` operator) -- no instance
   points-to of any kind exists in the kotlin resolver; this is a new
   points-to DIMENSION (object identity, not name-aliasing), not an
   extension of the existing file-wide name-alias table shape every other
   closure in this ticket reused.

Ran the full tests/test_vet.py suite (458 passed, 0 failed) after each
change and again at the end. gates-fast/gates-native/gates-security/lint/
static all pass under --ticket T-1063 except the pre-existing TICK006
(T-0667's own phantom-draft finding, unrelated to this ticket's scope,
unchanged before/after) and a pre-existing ruff-format warning on
tests/unit/test_arch.py (not touched by this ticket).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_struct_update_field_rebind_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_destructuring_declaration_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_default_parameter_forwarding_callable_detected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
