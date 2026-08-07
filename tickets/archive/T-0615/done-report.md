## Done report

Added the N:1 cross-language equivalence meta-test EPIC T-0329's own
acceptance criterion calls for: `tests/fixtures/arch/{python,typescript,
rust,kotlin}/equiv.{py,ts,rs,kt}`, four structurally-equivalent fixture
programs (base class/interface/trait, derived class with a field and one
overriding method, a long/complex `configure(_p|P)ipeline` function with
identical nested if/for/while shape, and a `dispatch(_k|K)ind` function
using each language's own idiomatic three-way dispatch construct --
if/elif, switch, match, when), plus `TestFourWayCrossLanguageEquivalence`
in `tests/unit/test_arch.py` adapting all four through `PythonAdapter`/
`TypeScriptAdapter`/`RustAdapter`/`KotlinAdapter` and asserting:

1. Entity-shape equivalence: every language's fixture yields exactly 2
   `NormalizedClass` entries (base + derived), and TS/rust/kotlin all
   capture the derived class's `name` field and `speak` method identically.
   `NormalizedFunction.overrides` is set to `"speak"` by TS/rust/kotlin's
   adapters (explicit `override` modifier / trait-impl inference) --
   pinned as an EXPECTED per-language DIFFERENCE for python, which has no
   static override keyword: `PythonAdapter` never sets `overrides` at all,
   asserted explicitly (`test_override_captured_except_pythons_documented_
   waiver`), not silently skipped.

2. Shared-check identical firing, four ways:
   `test_shared_complexity_check_fires_identically_four_ways` calls the
   SAME `_iter_normalized_functions`/`_normalized_is_complex` (migrated
   once in T-0610, reused unmodified by every prior pairwise test) against
   all four adapted modules' `configure_pipeline`/`configurePipeline` --
   all four fire `True`. A companion test proves the SAME dispatch
   function does NOT trip the complexity check in any of the four
   languages (a flat three-way dispatch is exactly what the rule must not
   punish, generalizing T-0289's match/case rationale across languages).

3. Per-language dispatch-branch-count divergence, pinned as EXPECTED:
   `test_dispatch_branch_counts_pin_the_documented_per_language_divergence`
   asserts python's if/elif dispatch scores 1 branch (tree-sitter-python
   folds an entire if/elif/else chain into ONE `if_statement` node, per
   `frob.arch._python`'s own `_BRANCH_NODE_TYPES` comment); TS's `switch`
   scores 0 branches (`switch_statement` is walked for nesting depth only,
   not one of `frob.arch._typescript`'s branch-producing node types);
   rust's `match` and kotlin's `when` both score 3 branches (each arm/
   entry counted individually, T-0612/T-0614's own documented
   divergences). Pinning all four side by side means any future adapter
   drift in EITHER direction on this shape fails loudly instead of
   silently.

REAL BUG FOUND, OUT OF SCOPE (`src/frob/arch/_python.py` is not in
T-0615's declared `scope`): while building the python fixture's class-level
annotated field (`name: str`), discovered `PythonAdapter._py_class_fields`
never actually detects it -- it gates on `c.type == "expression_statement"`
wrapping the assignment, but `tree-sitter-python`'s grammar hands the
`assignment` node back DIRECTLY as the class block's own named child, with
no `expression_statement` wrapper (verified directly: `PythonAdapter().
adapt(...)` on `class Foo:\n    x: int = 0\n` returns `classes[0].fields ==
[]`, always). No existing test caught this because `TestPythonAdapter`'s
real-fixture tests never assert on `.fields` via the adapter itself (only
a hand-built `NormalizedField` construction test exists, bypassing the
adapter entirely). Filed as T-0727 (ex-draft, id lost at land) (`uv run frob ticket new`,
parent T-0329, mints a real id at land) with scope
`src/frob/arch/_python.py,tests/unit/test_arch.py` and the concrete repro
in its body. The equivalence meta-test documents this as an observed
WAIVER for python's field-count comparison
(`test_python_field_detection_is_a_documented_waiver`) rather than
silently expecting parity with TS/rust/kotlin (which all genuinely
capture this shape); that waiver test must be updated to assert real
parity once T-0727 (ex-draft, id lost at land) lands its fix.

EPIC T-0329 implication: this was T-0329's own explicit closing acceptance
criterion ("an arch check written once fires correctly across
python+ts+rust+kotlin on equivalent code") and it now has a passing,
four-way pinned test proving it -- T-0329 is unblocked to close on its own
ticket, pending reviewer sign-off on this one (review-gated flow, not
closed here).

Gates: `uv run frob check --ticket T-0615` -- 0 errors, 401 warnings (190
waived), all pre-existing/unrelated to this ticket's scope (PERF/PII/REF/
SEC/WALK waived findings scattered across the repo, none touching
`tests/fixtures/arch/**` or the new `TestFourWayCrossLanguageEquivalence`
class). `gate:PRE` required one `frob ticket sweep T-0615` refresh after
adding the fixture files (PRE001 staleness), now clean. `ruff format` was
one file dirty (`tests/unit/test_arch.py`) before a plain `ruff format`
pass; both `ruff check`/`ruff format --check` and `ty check` clean after.
Deletion-filter (`git diff main --diff-filter=D --stat`) empty.

### Changed
```
 tests/fixtures/arch/python/equiv.py     |  96 ++++++++++
 tests/fixtures/arch/rust/equiv.rs       |  53 +++++
 tests/fixtures/arch/typescript/equiv.ts |  64 +++++++
 tests/unit/test_arch.py                 | 329 ++++++++++++++++++++++++++++++++
 tickets.md                              | 109 ++++++++++-
 5 files changed, 649 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_one_class_hierarchy_per_language` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_derived_class_has_the_field_and_one_method` (pytest node id, verified passing when recorded; T-0727 folded the former `test_python_field_detection_is_a_documented_waiver` waiver assertion into this test's now-4-way parity assertion once the underlying adapter bug was fixed)
- `tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_override_captured_except_pythons_documented_waiver` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_shared_complexity_check_fires_identically_four_ways` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_dispatch_branch_counts_pin_the_documented_per_language_divergence` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_every_module_agrees_the_dispatch_function_exists_and_is_flat` (pytest node id, verified passing when recorded)
