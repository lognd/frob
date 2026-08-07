---
id: T-1406
title: module_join_fraction denominator includes non-instrumentable repo-wide .py
  files, not just the --cov target
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: T-1406's fix needs a regression test verifying the coverage-root-scoped
    join denominator; adding the test file to scope rather than leaving the fix unverified
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_gates.py::TestCoverageLoad::test_module_join_fraction_excludes_files_outside_declared_cov_root
- tests/test_gates.py::TestCoverageLoad::test_scope_known_paths_no_declared_roots_falls_back_unchanged
designated_repro_test: null
acceptance:
- text: GIVEN a clean make coverage run over --cov=src/frob WHEN load_coverage computes
    module_join_fraction THEN the denominator only counts modules that could ever
    appear in coverage.xml under the measured --cov root(s), not every .py file in
    the repo
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_module_join_fraction_excludes_files_outside_declared_cov_root
- text: GIVEN module_join_fraction cannot be scoped this way for some reason WHEN
    a maintainer reads _module_join_fraction's docstring or the _DEFLATION_FLOOR comment
    THEN it explicitly documents that the denominator includes non-instrumentable
    files and why the floor still holds despite that
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_scope_known_paths_no_declared_roots_falls_back_unchanged
threat: null
component: null
---
T-1401 investigated frob-coverage.lock.json/coverage.xml disagreement and
found two distinct problems in src/frob/gates/_coverage.py. This ticket is
the second, deliberately NOT folded into T-1401's fix.

load_coverage's module_join_fraction (and the T-1180 deflation floor built
on it) treats "known .py modules" as every .py file _known_repo_paths finds
-- either the full graph snapshot's symbol paths, or a repo-wide
walk_pruned/_collect_file_hashes fallback that walks the ENTIRE checkout,
not just the --cov target. make coverage runs pytest with
--cov=src/frob (Makefile:233/238/242/305), so coverage.xml can structurally
never contain classes for tests/**, scripts, or anything outside
src/frob -- those files can never "join" no matter how healthy the run is.

Measured on the same 2026-08-01 clean run T-1401 diagnosed: exactly 447
files exist under src/frob (matching module_line's own joined count once
the ratchet bug is fixed), while _known_repo_paths reports 851 known .py
modules repo-wide (adding tests/** and friends, none of them ever
instrumented by --cov=src/frob). module_join_fraction=447/851=0.53 --
suspiciously close to the T-1180 _DEFLATION_FLOOR of 0.5, not because the
run is unhealthy but because the denominator is structurally wrong. A
future run that adds a handful more test files (routine) could cross this
floor and refuse every stamp, for a reason with nothing to do with
coverage health.

Fix: _module_join_fraction (or its caller) should compare module_line's
keys against the set of modules that are actually reachable under the
same root(s) coverage.xml's own <source> elements declare (or otherwise
scoped to what --cov could ever report), not every .py file in the repo.
Alternatively, if comparing against the full repo is intentional,
document module_join_fraction's docstring and the _DEFLATION_FLOOR
comment to say so explicitly and pick a floor that accounts for the
permanent non-instrumentable share, rather than leaving both silent about
the mismatch.