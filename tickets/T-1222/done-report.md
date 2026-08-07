## Done report

Delivered: `frob_core.py_function_metrics(source: bytes) -> [(span,
nesting, cyclomatic, events)]`, the rust arch python metrics single-pass
walk, extraction only -- rule evaluation (long-function/god-class/
deep-nesting thresholds, the T-0332 pattern detectors, lock-ordering/
async-hazard/shared-state-race/concurrency-model checks) stays entirely
in Python. Same design line T-1221's capability resolver states
explicitly, deliberately not repeated here as scope creep: this kernel
answers only "what does this function's body contain", replacing the
`_run_python_checks`-dominant portion of `_py_build_function`/`_py_build_
module` (measured 97 pct of archgate's own cost, `_py_build_module` alone
31 pct) currently computed as three separate Python recursions per
function (`_py_max_nesting`, `_py_cyclomatic`, `_py_collect_body_events`).

1. frob-core/src/arch_python.rs (new file, ~470 lines): one-pass-per-
   function native walk computing `((start_line, end_line),
   max_nesting_depth, cyclomatic, events)` where `events` is an 8-tuple
   of `branches`/`loops`/`calls`/`field_accesses`/`returns`/`raises`/
   `catches`/`subscripts` -- matching `NormalizedBranch`/`NormalizedLoop`/
   `NormalizedCall`/`NormalizedFieldAccess`/`NormalizedReturn`/
   `NormalizedRaise`/`NormalizedCatch`/`NormalizedSubscript`'s own field
   shapes exactly. Deliberately narrower than the full
   `NormalizedFunction` -- no `name`/`params`/`return_type`/`is_method`/
   `overrides`, each O(1) to read directly off the node and left
   Python-side (the ticket's own "extraction-only portion" framing).
   Every function (module-level, method, or nested) is flattened into
   one output list rather than mirroring `NormalizedFunction.nested_
   functions`'s tree shape, matching how a caller would want to iterate
   metrics without walking a second tree to find them.

   ONE DISCLOSED DEVIATION: `NormalizedCall.declared_raises` (T-0689's
   `# frob:callee-raises A, B` same-line comment convention) is never
   populated by this kernel -- a raw-text pattern layered on top of the
   tree walk, not a tree-sitter extraction concern; `_frob_raises_
   declaration` is a five-line pure function over `(call_line, source_
   lines)` a consumer can still run Python-side post-hoc, cheaply,
   without threading a second input through the FFI boundary. Documented
   in the module docstring and `docs/modules/arch.md`, and stripped
   identically on the Python comparison side of the golden test so the
   parity assertion is apples to apples.

2. frob-core/src/lib.rs: wired `py_function_metrics` into the
   `frob_core` `#[pymodule]` (twenty-first export).

3. frob-core/frob_core.pyi: typed stub for the new export (never raises,
   verified by `frob check --only ffi_boundary`: 0 errors/warnings).

4. docs/modules/arch.md (Normalized code model) + docs/modules/dup.md
   (frob-core kernel export count) describe the new kernel, its field-
   by-field mapping to the existing `NormalizedX` types, and the one
   disclosed deviation.

5. tests/unit/test_arch_python_native.py (new file, 5 tests): nested
   control-flow + `self.` field-access parity, a flat-function sanity
   check (zero nesting, low cyclomatic), nested-function-definition
   flattening, the never-raises contract, and a golden test against this
   repo's own `src/frob/arch/_python.py` -- byte-identical tuple-for-
   tuple against `_py_max_nesting`/`_py_cyclomatic`/`_py_collect_body_
   events`'s combined output, 0 mismatches.

Golden-test proof: every parity test asserts
`frob_core.py_function_metrics(source) == <python-side recomputation>`
directly (not an ad hoc script) -- `_python_side_metrics` runs the SAME
three existing Python functions this kernel replaces
(`_py_max_nesting`/`_py_cyclomatic`/`_py_collect_body_events`) and
reshapes their output into the identical tuple contract, so the
committed test IS the regression lock, not a one-time comparison.

FFI gate compliance: `frob check --only ffi_boundary` -- 0 errors, 0
warnings.

DUP001/WIRE001, fixed rather than waived where the underlying issue was
real, waived with a reasoned justification where it was a genuine
false-positive: ruff findings (unused import, ambiguous variable name
`l`) fixed outright. Four DUP001 findings (`branch_condition_text`,
`raise_exception_type`, `except_exception_type`, `collect_function_
metrics` vs. unrelated short tree-sitter helpers in `capability_python.rs`
and `extract.rs`, plus four unrelated strata-core parser methods) are the
SAME r2 structural-shape coincidence class T-1221 already hit and
disclosed -- generic "walk children, match node kind" shape matching
across small unrelated functions, not real duplication; each waiver
names the specific unrelated functions compared against and why they
share nothing but that shape. One WIRE001 on the golden-test comparison
helper `_python_side_metrics` (no production caller by design, same
`_python_side`/`_rust_side` precedent from T-1220/T-1221) -- widened
T-1503's existing scope to cover this file plus `test_capability_
native.py` (T-1221's own analogous helper, previously untracked) rather
than filing a near-duplicate ticket.

COV002 (same concurrent-overlapping-scope class T-1221's Done report
flagged as a property to watch for, not a defect): `frob-core/**` and
`tests/**`-shaped globs are scoped broadly by many tickets right now
(T-1219/T-1222 on `frob-core/**`; roughly thirty open tickets touch
`tests/**` in some form), so `_scope_covers`'s "unambiguous single
open-ticket scope match" rule cannot silently cover new symbols in
either new file. Fixed the same way: explicit `frob:ticket T-1222` edges
on every new/changed top-level symbol in `arch_python.rs`, `lib.rs`'s
changed `frob_core` registration, `design/frob.strata`'s `testsuite`
node, and every new symbol in `test_arch_python_native.py` (the test
file needed this too this time, unlike T-1220/T-1221's test files --
worth noting for the next wave: a NEW test file under `tests/unit/**`
is not automatically safe from this just because a sibling native-kernel
test file wasn't hit).

SELFAUDIT001: `design/frob.strata`'s `testsuite` node's `may "fs.write"`/
`"fs.read"` declarations extended to cover the new test file (writes/
reads a tmp fixture, same as every other `test_*_native.py` file's
pattern).

Also disclosed, unfixed (identical to T-1220/T-1221's own precedent,
non-systemic pattern): `tickets/T-1222/ticket.md` and (from the T-1503
scope widen) `tickets/T-1503/ticket.md` show a SCOPE001 under `--only
scope` while T-1222 is actively in-progress -- resolves the same way at
land, not a new class of issue.

Filed: none -- no out-of-scope work discovered this pass.

Gates: `frob check --ticket T-1222 --only scope --only prework --only fmt
--only affect_drift --only ffi_boundary` -- 0 errors besides the two
known, disclosed, non-systemic `ticket.md` SCOPE001 findings above.
`frob check --land-parity` -- clean, 0 unscoped errors.

Status: leaving T-1222 IN-PROGRESS for the coordinator/reviewer to close
after land, per this repo's review-gated ticket workflow -- not closing
it myself.

### Changed
```
 design/frob.strata                    |   5 +-
 docs/modules/arch.md                  |  39 +++
 docs/modules/dup.md                   |   5 +
 frob-core/frob_core.pyi               |  36 +++
 frob-core/src/arch_python.rs          | 465 ++++++++++++++++++++++++++++++++++
 frob-core/src/lib.rs                  |   6 +
 tests/unit/test_arch_python_native.py | 170 +++++++++++++
 tickets/T-1222/ticket.md              |  48 +++-
 tickets/T-1503/ticket.md              |  20 ++
 9 files changed, 790 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_control_flow_and_self_field_access` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_flat_function_has_zero_nesting_and_low_cyclomatic` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_nested_function_definition_is_flattened_into_own_entry` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity::test_this_repos_own_arch_python_module_matches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 982 warning(s), 736 waived
- error-findings: none (measured, zero errors)
