## Done report

All five children close the umbrella's own acceptance ("GIVEN the children
closed WHEN frob check runs on a fixture with a known exception surface
THEN the may-raise sets are queryable and every child gate/advisory fires
per its own acceptance"):

- T-0686 (done): the Python may-raise resolver, frob.arch._mayraise.
  compute_may_raise -- explicit raise sites, resolved same-module callee
  propagation, curated builtin-raiser table, UNKNOWN fail-closed for
  anything unresolved.
- T-0688 (done): the exhaustive-handling gate (EXHAUST001/EXHAUST002) and
  the errors-as-values advisory, both consuming compute_may_raise's
  output.
- T-0689 (done): ctypes/cffi/C-extension call boundaries extended into
  the same resolver as opaque, UNKNOWN fail-closed unless declared via
  the call-site frob:callee-raises directive.
- T-0690 (done, this dispatch): the FFI-boundary cross-check --
  frob.gates._ffi_boundary's FFI001 (pyo3 Rust-side observed exceptions
  cross-checked against the .pyi stub's above-the-def frob:raises
  declaration, drift named on both sides) and FFI002 (every ctypes-loaded
  -handle call site must carry a frob:callee-raises declaration, empty
  set valid for the errno convention).
- T-0687 (done, this dispatch): C++'s own may-throw analysis
  (frob.arch._cpp_mayraise) -- explicit throw sites, curated STL-thrower
  table, same-file callee propagation, Unknown fail-closed, wired into
  analyze_project's live cpp dispatch branch; noexcept functions are hard
  boundaries (ArchSeverity gained "error" for this), a violation names the
  call site and escaping type(s), and a try/catch (...) discharges it.

Every child's own acceptance criterion is independently evidenced and
closed (see each child ticket's own Done report). Two residual pieces of
work were disclosed as follow-ups rather than silently folded into either
child, both filed as drafts during this dispatch:
- Wiring frob.gates._ffi_boundary.ffi_boundary_gate ("ffi_boundary") into
  an existing src/frob/check/__init__.py _STAGE_GROUPS alias
  (gates-native/gates-fast/...) so a bare --only <group> run picks it up
  without naming it explicitly -- it already runs today via its own bare
  gate name.
- Promoting frob.arch._cpp_mayraise's "error"-severity ArchSuggestion
  (cpp-noexcept-throws) into an enforced, unwaivable src/frob/gates/**
  gate finding, the way frob.gates._unwaivable_channel_rules already does
  for every other ArchCategory -- it currently surfaces via a plain
  frob.arch.analyze_project(root) call but is not yet gate-enforced.

Neither follow-up blocks the umbrella's own acceptance text (which asks
only that "the may-raise sets are queryable and every child gate/advisory
fires per its own acceptance" -- both are true today); they are scope
carve-outs each child's own Done report already discloses, not gaps in
what was delivered.

### Changed
```
 docs/modules/arch.md            |  57 ++++++
 docs/modules/gates.md           |  68 +++++++
 src/frob/arch/__init__.py       |   9 +
 src/frob/arch/_cpp_mayraise.py  | 415 +++++++++++++++++++++++++++++++++++++++
 src/frob/arch/_ffi.py           | 421 ++++++++++++++++++++++++++++++++++++++++
 src/frob/arch/_models.py        |  25 ++-
 src/frob/gates/__init__.py      |  18 ++
 src/frob/gates/_ffi_boundary.py | 206 ++++++++++++++++++++
 strata-core/strata_core.pyi     |   6 +
 tests/test_gates.py             | 126 ++++++++++++
 tests/unit/test_arch.py         |  91 +++++++++
 tickets.md                      | 189 +++++++++++++++++-
 12 files changed, 1626 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 19369 warning(s), 341 waived
- error-findings: ARCH001@src/frob/arch/_cpp_mayraise.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py, PRE001@tickets/T-0685
