## Done report

T-1450 delivers the per-may-via SYS101 join the T-1440 landing deliberately
deferred: `_stale_design_violations` (src/frob/strata/_selfconform.py) now
iterates each node's `may_grants` individually instead of the flat,
kind-deduped `_raw_declared_kinds` set. A via-scoped grant is judged stale
only against the files its own `via` glob(s) cover (`_via_matches`, reused
from `_effects.py`); a via-less grant keeps the pre-T-1440 whole-node join
unchanged. `node.may_grants` empty entirely (hand-built `Node` fixtures
that bypass the parser) falls back to the old whole-node-only path exactly
as before -- zero behavior change for anything that predates T-1440's
grammar.

To give the per-via join something to narrow, `_observed_raw_kinds_by_node`
is split into a per-file scan (`_observed_raw_kinds_by_file`, the actual
`scan_file_capabilities` loop) plus a thin per-node aggregate
(`_aggregate_raw_kinds_by_node`) -- `_collect_sys_violations` now scans
once at file granularity and derives both the node-level view (for SYS100
extended / SYS105 purpose) and the new file-level view (for SYS101) from
that one pass, preserving the T-0830 single-scan discipline. The one other
caller of the old node-level-only path, `_mutation_audit.py`'s SYS101
baseline count, was updated to the same file-level join.

Two new unit tests exercise the acceptance clause directly: a grant scoped
to file A that A never exercises is stale even though file B (same node,
same kind) does exercise it; a via-less grant on the same kind still
discharges via ANY file, unchanged.

Evidence: `tests/unit/strata/test_selfconform.py::TestStaleDesign::test_via_scoped_grant_stale_while_other_surface_uses_same_kind`,
`tests/unit/strata/test_selfconform.py::TestStaleDesign::test_via_less_grant_alongside_via_grant_still_discharges_whole_node`
(both pass, plus the full `tests/unit/strata/test_selfconform.py` suite,
69 tests, all green). `tests/unit/strata/test_mutation_audit.py::
TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds`
was confirmed failing identically on unmodified HEAD before this change
(swap-file diff performed directly, not via `git stash` -- the shared-
`refs/stash` hazard) -- pre-existing, unrelated to this ticket, not
touched here.

LAND-REPAIR ADDENDUM (post-T-1456 sweep): wrapped the two E501 lines in
src/frob/strata/_selfconform.py the sweep flagged (:534, :879 as of the
pre-merge main tip -- `_observed_raw_kinds_by_node`'s return statement and
`_stale_design_violations`'s `found.extend(...)` call), and applied `ruff
format` to this file (a `has_via_less` conditional reflow, no behavior
change). Also sorted the StrataScopeConfig import ruff flagged in
src/frob/strata/__init__.py. No functional change.

### Changed
```
 design/frob.strata                                 |   6 +
 docs/design/registry/check-coverage.yaml           |   6 +-
 docs/modules/gates.md                              |   6 +-
 docs/modules/graph.md                              |   4 +-
 docs/modules/strata.md                             |  24 ++
 docs/strata/surface.md                             |  43 ++-
 src/frob/gates/_sys_selfaudit.py                   |  39 +-
 src/frob/gates/_waive.py                           |   3 +
 src/frob/strata/__init__.py                        |   5 +
 src/frob/strata/_mutation_audit.py                 |  19 +-
 src/frob/strata/_scope_config.py                   |  70 ++++
 src/frob/strata/_selfconform.py                    | 321 ++++++++++++++---
 tests/unit/gates/test_sys_selfaudit.py             |  51 +++
 tests/unit/strata/test_scope_config.py             |  46 +++
 tests/unit/strata/test_selfconform.py              |  68 ++++
 .../unit/strata/test_sys107_via_scope_advisory.py  | 117 ++++++
 tickets.md                                         | 392 ++++++++++++++++++++-
 17 files changed, 1139 insertions(+), 81 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestStaleDesign::test_via_scoped_grant_stale_while_other_surface_uses_same_kind` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestStaleDesign::test_via_less_grant_alongside_via_grant_still_discharges_whole_node` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
