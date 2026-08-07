## Done report

Denominator reconciliation: docs/design/capability-evasion-taxonomy.md's
own "Combined coverage table" states 112 entries (13+9 Python, 17+9
TS/JS, 13+6 Rust, 7+5 C, 12+5 C++, 11+5 Kotlin), exactly matching
docs/design/registry/evasion.yaml's 112 EVA-<LANG>-<S|R><NN> ids (grep
count confirmed). One real, previously-undocumented mismatch found and
NOT silently resolved: Python's own subsection TABLE (not the summary
line) has 14 static-resolvable rows and 10 runtime-opaque rows (24 total,
grep `^| static |` / `^| runtime |` counts), two more than the 13+9=22 its
own summary line states. The likely explanation (not authoritatively
resolved, since docs/design/capability-evasion-taxonomy.md is outside
this ticket's declared scope): the "`as` in `with`/`except`" static row
is explicitly flagged in its own doc text as "(binding pattern, not
itself dangerous but part of the same bind family)" -- probably
deliberately uncounted; and the "direct `sys.modules` replacement"
runtime row was added in a later Phase-2 pass whose summary total (105 ->
112) was bumped but whose PYTHON-SPECIFIC "13 static, 9 runtime" line was
apparently never re-bumped alongside it. Both candidate rows nonetheless
GOT a litmus fixture in this pass (test_with_as_binding_a_callable_bearing_object_detected,
test_python_sys_modules_replacement_not_addressed) -- bonus coverage
beyond the registered 112, not a gap. Flagged here as a documentation-
accuracy finding for the doc's own owner; not filed as a separate ticket
since it is purely a stated-count-vs-table-row-count inconsistency with
zero code impact (the registry's 112 already matches the doc's own
stated total, which is what T-1047 and this pass's litmus
count-floor both anchor to).

Method: for each of the 112 registered entries (grouped by
language+category, since the source doc assigns no stable per-row id of
its own -- RECONCILIATION.md finding (a) -- the registry's own ids were
MINTED, not authored, so a literal per-row 1:1 zip would be fragile/
unverifiable), located or wrote a litmus fixture in tests/test_vet.py.
30 pre-existing fixtures already covered a construct; 47 NEW fixtures
were added this pass (listed below by language). Genuine denominator
gaps found (constructs the analyzer does NOT currently resolve / does NOT
fail closed on) were NOT silently passed -- each got a fixture that locks
the CURRENT honest non-detection, with an inline docstring explaining the
gap, and are consolidated into a single follow-up ticket,
T-1047 (renumbered at land).

New fixtures added this pass (47), by language:

Python (3 new): closure capture, `with ... as` binding, walrus operator
-- all 3 resolve correctly (bonus rows beyond the registered 13, per the
reconciliation finding above). Plus 7 new runtime-opaque fixtures: exec,
`__import__` computed, setattr/monkeypatch (all 3 fire correctly);
container-dynamic-key, functools.partial, class `__getattr__`
interception, sys.modules replacement (all 4 are genuine gaps -- no
RUNTIME_OPAQUE_CONSTRUCTS entry exists for them).

TypeScript/JS (5 new static): named-import-alias, export-from re-export,
export-star-from re-export, export-default binding, class-field holding a
bound reference -- all 5 resolve, via the scanner's existing file-wide
member-expression over-approximation (not true cross-module/points-to
resolution, documented per-test). Plus 8 new runtime-opaque fixtures:
eval, Function constructor (both fire correctly); computed-member
non-constant-key, globalThis[name], Reflect.get/apply, Proxy interception,
container-dynamic-key, monkeypatch-module-namespace (all 6 are genuine
gaps).

Rust (4 new static): function-pointer coercion from named fn, type alias
for fn-ptr type (both resolve, reduce to the same `let`-binding path);
struct-update field rebinding (GENUINE GAP -- no struct-field points-to
exists); macro_rules! expansion (GENUINE GAP -- no macro-expansion-aware
resolution exists at all for Rust). Plus 5 new runtime-opaque fixtures:
trait-object dynamic dispatch (bounded-polymorphism, correctly silent by
design), extern-block FFI symbol (GENUINE GAP -- source-invisible but
NOT yet excused in OPAQUE_SOURCE_INVISIBLE), function-pointer-in-
container, Box<dyn Fn> runtime-selected, proc-macro-synthesized call (all
3 genuine gaps). Plus 1 fixture locking the existing rust vtable-patch
OPAQUE_SOURCE_INVISIBLE excuse.

C (0 new static -- all 7 rows already had fixtures). 3 new runtime-opaque
fixtures: non-constant array index, integer-cast to fn ptr, void*
backcast (all 3 genuine gaps). Plus 1 fixture locking the existing C
weak-symbol OPAQUE_SOURCE_INVISIBLE excuse.

C++ (4 new static): using-namespace directive, #define macro aliasing
(cpp extension), argument-dependent lookup (all 3 resolve); member-
function-pointer bound to a named member (GENUINE GAP -- no
pointer-to-member alias tracking exists). Plus 4 new runtime-opaque
fixtures: array/vector runtime index, reinterpret_cast, RTTI dispatch
(all 3 genuine gaps); virtual dispatch (correctly silent, bounded
polymorphism by design).

Kotlin (5 new static): destructuring declaration, lambda/closure
capturing a bound name, default-parameter forwarding, extension-function
reference via import, operator fun invoke (lambda-capture and
extension-fn-ref resolve; destructuring, default-param-forwarding, and
operator-fun-invoke are GENUINE GAPS -- no destructuring-declaration
alias tracking, no parameter-default alias tracking, no receiver-instance
points-to exists). Plus 3 new runtime-opaque fixtures: function-value-in-
container, delegated-property-by, dynamic-classloading (all 3 genuine
gaps); plus 1 fixture for KCallable.call (fires correctly, was untested
despite having a registered detector).

Meta-test (new): tests/test_vet.py::TestEvasionTaxonomyExhaustiveness (5
tests) -- parses capability-evasion-taxonomy.md's per-language tables AT
TEST TIME (frob.vet._evasion_coverage._DOC_HEADING_TO_LANGUAGE_KEY /
_EVASION_LITMUS_MAP is the explicit, greppable, statically-checkable
registration structure the ticket brief asked for) and asserts: (1) every
(language, category) bucket's doc row COUNT never exceeds the registered
litmus-path count for that bucket (acceptance [1]: a new taxonomy row
with no matching fixture fails the build); (2) every listed dotted
"Class.method" path resolves to a real, collected test via `ast` parsing
(dangling-ref direction); (3) every known-language doc heading is
recognized (stale-heading guard); (4) no orphaned (language, category)
key exists in the map with zero matching doc rows (typo guard); (5) the
combined registered total is >= 112 (the reconciled denominator).
Guarantee shape is bucket-count sufficiency, not a strict per-row 1:1 id
assignment (documented honestly in the module's own docstring, since the
taxonomy doc itself assigns no stable per-row id -- a literal 1:1
assignment would require fragile assumptions about doc-table row order
matching registry id-minting order, which this pass deliberately avoided
relying on for correctness).

Filed: T-1047 (renumbered at land) -- consolidates every
genuine gap found this pass (~19 runtime-opaque constructs across 5
languages with no detector/excuse; 1 Rust struct-field points-to gap; 1
Rust macro_rules! gap; 1 C++ pointer-to-member gap; 3 Kotlin resolver
gaps) into one tracked follow-up, scoped to extend
RUNTIME_OPAQUE_CONSTRUCTS / OPAQUE_SOURCE_INVISIBLE / the per-language
resolvers. Each gap's litmus fixture in tests/test_vet.py cross-
references T-1047 by name in its own docstring.

Gates: `frob check --ticket T-0666 --only coverage` clean of new errors
(2 new COV001 findings on the new module's public constants were fixed
by making them private, `_DOC_HEADING_TO_LANGUAGE_KEY`/
`_EVASION_LITMUS_MAP`, since docs/modules/vet.md is outside this ticket's
declared scope to add a frob:doc anchor to; remaining COV001/PERF/ARCH
errors in the full-repo `--only gates-native`/`--only gates-fast` output
are pre-existing, unrelated to any file this ticket touched -- verified
by file path in every remaining unwaived finding). `frob check --ticket
T-0666 --only gates-native` and `--only gates-fast` both show zero
unwaived findings touching src/frob/vet/**, docs/design/registry/
evasion.yaml, or tests/test_vet.py. Full `pytest tests/test_vet.py`
(1795+ collected across all classes, xdist 12 workers) passes clean,
multiple times across this session including once after merging main
forward from dfd61c26 to 3743a298 mid-ticket to pick up sibling-landed
work (T-1034/T-1040/T-1041/T-1042/T-1043/T-1044/T-0757), with
`git diff main --diff-filter=D` empty and `git diff main --stat` showing
only this ticket's own 4 files.

### Changed
```
 docs/design/registry/evasion.yaml |  238 ++++----
 src/frob/vet/_evasion_coverage.py |  206 +++++++
 tests/test_vet.py                 | 1109 +++++++++++++++++++++++++++++++++++++
 tickets.md                        |   94 +++-
 4 files changed, 1534 insertions(+), 113 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_doc_heading_recognized` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_litmus_path_resolves_to_a_real_test` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_map_has_no_orphaned_language_category_pairs` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_combined_registered_total_matches_112_entry_denominator` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_closure_capture_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_with_as_binding_a_callable_bearing_object_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_walrus_operator_bind_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_export_from_reexport_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_export_star_from_reexport_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_export_default_binding_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_class_field_holding_bound_reference_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_named_import_with_alias_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_function_pointer_coercion_from_named_fn_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_type_alias_for_function_pointer_type_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_struct_update_field_rebind_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_macro_rules_expansion_emitting_fixed_call_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_namespace_directive_qualified_call_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_define_macro_aliasing_detected_on_cpp_extension` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_member_function_pointer_bound_to_named_member_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_argument_dependent_lookup_call_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_destructuring_declaration_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_lambda_closure_capturing_bound_name_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_default_parameter_forwarding_callable_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_operator_fun_invoke_making_object_directly_callable_not_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_exec_always_fires_regardless_of_argument` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_setattr_monkeypatch_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_container_dynamic_key_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_eval_always_fires_regardless_of_argument` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_function_constructor_always_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_integer_cast_to_function_pointer_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_void_star_backcast_not_addressed` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_weak_symbol_override_excused_source_invisible` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_runtime_vtable_patch_excused_source_invisible` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_cpp_virtual_dispatch_bounded_polymorphism_no_finding` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_kotlin_kcallable_call_always_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 36 passed (from 36 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
