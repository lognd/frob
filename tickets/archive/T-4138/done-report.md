## Done report

Evidence: tests/gates_suite/test_test_gate.py::TestNativeTestCollectors
  ::test_test002_unmeasured_when_ts_collector_failed (MUST-FIRE)
  ::test_test002_still_fires_when_collector_did_not_fail (MUST-STAY-QUIET)
  ::test_test002_absent_vs_measured_zero_render_differently (THIRD FIXTURE)
  ::test_load_tests_merges_all_four_collectors (regression, updated for
    the new 3-tuple _load_tests return)
  ::test_ts_structural_only_edge_no_longer_credited (regression: with
    failed_test_languages=frozenset() default, unchanged behavior)
All five pass under uv run pytest; frob test --base main: PASS (touched
python suite, exit=0).

Audit (acceptance item 4): the shared CollectedTests loader
(_valid_edges/_case_count) has FOUR other consumers with the identical
conflation, none fixed by this ticket -- TEST001's naming-convention
(no-edge) path, TEST003 (integration), TEST004 (e2e, Severity.ERROR --
the most consequential instance, since it blocks frob check rather than
warning), and TEST009 (design e2e). Filed as a follow-up ticket (draft
id T-4176, real T-#### assigned on next renumber -- title
"Generalize TEST002's absent-vs-measured-zero fix (T-4138) to
TEST001/003/004/009"). The shared CoverageData loader was also audited:
TEST001's branch-coverage override and the TEST005 family already had
the correct absent-vs-measured-zero posture before this ticket (that
correct code is what this ticket's fix for TEST002 mirrors) -- zero
additional CoverageData conflations found.

Non-python reporter decision (acceptance item 3): ALREADY DONE, no
action needed. collect_ts_tests (src/frob/testing/_collect_ts.py,
outside this ticket's scope, read-only) already counts collected vitest
cases from `npx vitest list --json` -- the runner's own JSON reporter --
and never demands a python-shaped coverage.xml from the TS stack. This
ticket's own root-cause investigation confirms TEST002's count path
(_case_count/_valid_edges) reads tests: CollectedTests, never
CoverageData -- the F-340 report's "no coverage artifact" is imprecise
language for "no successful vitest collection this run" (an npx/
project-discovery/subprocess failure degrading collect_ts_tests's
Result to Err, which _load_tests previously swallowed into an
indistinguishable empty node-id set for rust/ts/cpp alike, unlike
python's already-distinguished python_collection_failed -> COV003
path). No coverage.xml-related fix was needed or made.

Filed: T-4176 (see Audit above)
Gates: frob check --ticket T-4138 -- gate:TEST clean (0 errors, 0
  unresolved beyond the intended UNRESOLVED verdicts, my fixtures'
  scope). Repo-wide FAILs present in the same run (gate:SCOPE 248,
  gate:ARCH 1, gate:COV 1, gate:CROSSTICKET 1, gate:DRIFT 2, gate:PRE
  formerly 1 (cleared by frob ticket sweep), ruff-format 34 files) are
  PRE-EXISTING / caused by declaring the shared docs/modules/gates.md
  and src/frob/gates/__init__.py in scope, not by this ticket's diff:
  - gate:SCOPE's 248 errors are scope-closure cascade from
    docs/modules/gates.md's hundreds of PRE-EXISTING frob:doc/describes
    anchors across the whole repo (confirmed at `frob ticket scope
    --add` time, before any T-4138 edit landed, by the same warning
    firing against the untouched file) -- any ticket declaring
    gates/__init__.py in scope hits this, since gates.md is its doc
    target and gates/__init__.py's frob:doc network spans the repo.
    Not attempted to resolve here: would require scoping ~250 unrelated
    files, clearly wrong for a targeted bug fix.
  - gate:ARCH/gate:COV/gate:CROSSTICKET/gate:DRIFT errors found above
    name unrelated symbols (_lang_conformance.py, _rule_id_scan.py,
    _python.py, frob.lock/T-3799's own in-progress lease) never touched
    by this ticket's diff.
  - ruff-format's 34 files is repo-wide drift outside this diff (the 2
    files this ticket touches are ruff-format-clean, verified directly
    with `frob format`).
  gate:TEST itself: 0 errors, 0 unresolved (beyond this ticket's own
  intended UNRESOLVED verdicts in its fixtures), matching pre-ticket
  baseline plus the new fixtures.

### Changed
```
 docs/modules/gates.md               |  62 ++++++++++++-
 frob.lock                           |  25 +++++-
 src/frob/gates/__init__.py          | 175 +++++++++++++++++++++++++++++++++---
 tests/gates_suite/test_coverage.py  |   6 +-
 tests/gates_suite/test_test_gate.py | 115 +++++++++++++++++++++++-
 tickets/T-4138/ticket.md            |  12 +++
 tickets/T-4176/ticket.md  |  58 ++++++++++++
 7 files changed, 436 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_test002_unmeasured_when_ts_collector_failed` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_test002_still_fires_when_collector_did_not_fail` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_test002_absent_vs_measured_zero_render_differently` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_load_tests_merges_all_four_collectors` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_ts_structural_only_edge_no_longer_credited` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 6 error(s), 4519 warning(s), 935 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/vet/_bare_toolchain.py, CROSSTICKET001@frob.lock, DRIFT001@src/frob/gates/_rule_id_scan.py, DRIFT002@src/frob/check/_python.py, SCOPE002@tickets.md
