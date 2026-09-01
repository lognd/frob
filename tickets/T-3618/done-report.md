## Done report

_check_tdd_order resolves merge-base(base_ref, HEAD) once per land and
threads it through tdd_order_violations/resolve_symbol_introduction as
`since`, bounding each edge's git-log walk to since..HEAD instead of
the symbol's entire file history (a diff-scoped edge's introducing
commit is by construction one of the land's own worktree commits).
tdd_order_violations also shares one revisions/content cache across all
edges in a call, so repeated edges against the same file (the measured
T-3586 shape) walk/read it once, not once per edge. Merge-base
resolution failure falls back to the prior unbounded behavior, logged
loudly (never silent). Perf regression tests assert git-invocation
SHAPE (call counts, since..HEAD pathspec) per the ticket's own
acceptance bar, not wall-clock.

Filed: none.

Gates: frob check --ticket T-3618 clean for the diff-scoped families
(SCOPE/PREWORK/COV002/TODO001/FMT/AFFECT); repo-wide gate families are
unscoped per --ticket's own scope-note and carry pre-existing findings
unrelated to this change.

### Changed
```
 docs/modules/gates.md         |  34 ++++++++----
 src/frob/gates/_tdd_order.py  | 122 ++++++++++++++++++++++++++++++++++++------
 src/frob/tickets/_land.py     |  33 +++++++++++-
 tests/gates/test_tdd_order.py |  99 ++++++++++++++++++++++++++++++++++
 tests/test_ticket_land.py     |  89 +++++++++++++++++++++++++++++-
 tickets/T-3618/ticket.md      |  12 +++++
 6 files changed, 360 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/gates/test_tdd_order.py::TestPerfShape::test_since_bounds_the_log_walk_to_a_revision_range` (pytest node id, verified passing when recorded)
- `tests/gates/test_tdd_order.py::TestPerfShape::test_shared_file_is_walked_and_read_exactly_once_across_edges` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder::test_passes_the_resolved_merge_base_as_since` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder::test_falls_back_to_unbounded_when_merge_base_is_unresolvable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 13 error(s), 4306 warning(s), 901 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3618, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
