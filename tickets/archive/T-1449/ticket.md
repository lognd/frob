---
id: T-1449
title: 'test_selfconform.py full-repo-scan tests: reduce peak memory or generalize
  xdist grouping'
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_selfconform.py
- src/frob/strata/_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
designated_repro_test: null
threat: null
component: null
---
Found while working T-1448 (main suite red: 14 failures).

tests/unit/strata/test_selfconform.py::TestCoverageTotality::
test_repo_unrestricted_scan_is_clean and TestRealGateGreen::
test_repo_design_and_declarations_are_self_conformant each run a full,
unrestricted repo capability scan costing ~400MB peak RSS / ~20s wall in
isolation. Under `-n auto` these two can land on separate xdist workers
concurrently, a plausible mechanism for the worker crash observed in the
2026-08-02 14:19 make coverage run (gw1) and a prior run (gw0, different
test in the same family).

T-1448 mitigated this by xdist_group-pinning both tests to the
same worker (via --dist=loadgroup in pyproject.toml addopts) so their
peaks serialize instead of coinciding -- but this does not reduce either
scan's own footprint, and any other two large tests could still coincide
on separate workers.

Two follow-ups worth investigating separately:
1. Reduce _sorted_capability_files/_coverage_totality_violations's own
   peak memory (e.g. streaming instead of materializing the full sorted
   file list, or avoiding redundant tree-sitter re-parses across the two
   tests' back-to-back full scans).
2. A general "heavy test" xdist grouping convention (or a documented
   playbook section) so future full-repo-scan-shaped tests get the same
   protection by default instead of requiring a human to notice and tag
   them individually.