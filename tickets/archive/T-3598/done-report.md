## Done report

Changed:
src/frob/refactor/_verify.py::_import_check_env (frob:waive ARCH103 removed, dead)
tests/unit/test_arch_srp.py::TestArch103WaiverStaysEffective

Evidence:
tests/unit/test_arch_srp.py::TestArch103WaiverStaysEffective::test_import_check_env_arch103_no_longer_fires_raw
tests/unit/test_arch_srp.py::TestArch103WaiverStaysEffective::test_waiver_mechanism_resolves_a_genuine_arch103_by_exact_symbol
tests/unit/test_arch_srp.py::TestArch103WaiverStaysEffective::test_git_head_sha_arch103_is_waived

Root cause confirmed: T-3587 (feat land d14c3a98f) moved _import_check_env's
src-vs-repo-root branch out into a separate import_roots() helper, dropping
this function's own decision-point count from 2 to 1 -- below ARCH103's
MIXED_CONCERN_MIN_DECISION_POINTS=2. Not a detector regression: the function
genuinely lost the second decision point. _git_head_sha's twin waiver was
unaffected (still trips ARCH103, still resolved by its own waiver).

Fix: removed the now-dead frob:waive ARCH103 comment from _import_check_env
(with a T-3598 comment recording why); replaced the old test (which
asserted ARCH103 still fires raw on the real function) with (1) a
discharge-lock test asserting it no longer fires raw, and (2) a synthetic
fixture test that keeps proving the general waiver-stays-bound-to-exact-
symbol mechanism without depending on the real function's shape staying
put across future refactors.

Filed: none

Gates: frob check --ticket T-3598 clean on gate:SCOPE/gate:PRE (sweep
refreshed); `frob test` exceeded its 540s budget and was not relied on --
verification is the 3x-clean scoped pytest run above instead. Repo-wide
gate:WAIVE/etc failures from an unscoped run are pre-existing (T-3590).
