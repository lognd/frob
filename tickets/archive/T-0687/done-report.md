## Done report

Same may-set shape as T-0686 (Python) and T-0690 (pyo3 boundary) applied
to C++'s own exception model: new frob.arch._cpp_mayraise, a raw-text
scan (deliberate -- no NormalizedModule adapter exists for C++, standing
one up is out of proportion to this ticket's own scope) that finds
explicit throw sites, curated STL throwers (.at -> out_of_range, new ->
bad_alloc, std::sto* -> invalid_argument), and propagates through
same-file callee references via an iterative fixpoint; anything else
(virtual/indirect/function-pointer calls) is Unknown, fail-closed, per
T-0665's established obligation-pattern precedent.

noexcept functions are hard boundaries, not advisory: check_cpp_
noexcept_violations fires an ArchSuggestion (category
cpp-noexcept-throws) for a noexcept function whose computed may-throw set
is non-empty and not discharged by its own catch (...). ArchSeverity
gained a new "error" value (T-0687; previously warning/suggestion/info
only) since an escaping exception from noexcept is std::terminate at
runtime, not an advisory concern -- but promoting an "error"-severity
ArchSuggestion into an enforced, unwaivable src/frob/gates/** gate
finding (the way frob.gates._unwaivable_channel_rules already does for
every OTHER ArchCategory) is gates/** wiring, out of this ticket's
declared scope (arch/**, lang/**, tests/unit/test_arch.py only) -- filed
as a follow-up (draft T-1034), same T-0728/T-0688 "built and
tested first, wiring later" precedent this package already uses
repeatedly.

Wired into analyze_project's live "cpp" dispatch branch
(frob.arch.__init__._analyze_one_file) -- a plain
frob.arch.analyze_project(root) call already surfaces these findings; no
gates/** change needed for that half.

docs/modules/arch.md was scope-added (frob ticket scope --add) alongside
tests/unit/test_arch.py's own already-declared scope, for the new public
symbols' frob:doc coverage (COV001) -- both are evidence/doc-coverage
additions, same convention the playbook's "scope-add evidence test
files" instruction already covers.

Full soundness needs libclang eventually (disclosed per the parent
ticket's own acceptance text) -- a tree-sitter-level text scan cannot
resolve overload sets, templates, or cross-translation-unit calls; the
Unknown fail-closed default is the approximation the parent ticket
explicitly asked for, not a to-be-improved placeholder in this ticket.

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
 tickets.md                      | 118 ++++++++++-
 12 files changed, 1555 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_with_catch_all_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCppMayThrow::test_non_noexcept_function_never_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_vector_at_fires_curated_thrower` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 2726 warning(s), 341 waived
- error-findings: ARCH001@src/frob/arch/_cpp_mayraise.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
