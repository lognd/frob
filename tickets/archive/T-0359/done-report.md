## Done report

Changed:
- src/frob/arch/__init__.py::_is_test_file (new, documented duplicate of
  frob.gates._is_test_file / frob.testing._select._is_test_file's
  name/dir heuristic)
- src/frob/arch/__init__.py::_analyze_one_file (computes is_test once per
  file, skips cpp long-function/god-class checks when is_test)
- src/frob/arch/__init__.py::_run_python_checks (skips python
  long-function/god-class checks and signature accumulation -- which
  feeds the cross-file abstraction-opportunity pass -- when is_test;
  high-coupling and deep-nesting still run on test files, unchanged)

high-coupling and deep-nesting were intentionally left running on test
files -- only long-function, god-class, and abstraction-opportunity (the
three categories T-0204/T-0359 named as test-nature noise) are exempted.

Evidence:
- tests/unit/test_arch.py::TestTestFileExemption::test_test_file_no_long_function_or_god_class
- tests/unit/test_arch.py::TestTestFileExemption::test_equivalent_src_file_still_flagged
- tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render

Measured counts (uv run frob check --only arch, full repo):
- Before: not independently re-measured on this exact tree (ticket's
  triage baseline: ~51 test-file warnings, 28 abstraction-opportunity +
  23 long-function/god, from T-0204's decomposition).
- After: `grep -iE "abstraction-opportunity|long-function|god-class"` over
  the arch stage's output found 110 total advisory findings, ALL under
  src/ (0 under tests/). Full `uv run frob check --ticket T-0359` gates
  stage: 0 errors, 19 warnings, 34 waived.
- Control test (test_equivalent_src_file_still_flagged) proves the same
  long-function/god-class fixture content still fires when placed under
  src/ with a non-test name, confirming src categories are not weakened.

Filed: none (fix stayed within declared scope; no new out-of-scope work
found).

Gates: `uv run frob check --ticket T-0359` clean (0 errors, 19 warnings,
34 waived, all pre-existing/unrelated -- PERF/PII/SEC waived notes and
TEST006/TEST009 informational warnings). `uv run frob test --base main`
selected and ran tests/unit/test_arch.py's 3 touched-set node ids,
exit=0, 2.17s.
