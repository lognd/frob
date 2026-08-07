## Done report

REDO ADDENDUM (2026-08-03): the prior Done report on this ticket claimed
a 46-grant may-to-via migration of design/frob.strata, but the edit
never actually reached this branch -- HEAD's design/frob.strata was
still 100% whole-node (via-less) may grants across every node, and
`frob check --only sys` at that commit still showed all 8 SYS107
warnings. The migration described in the prior report was lost, most
likely to a git-stash mishap in an earlier session on this shared
worktree/branch class (the exact hazard docs/guides/agent-playbook.md
section 1b documents) -- committed-but-never-actually-there is the
observed symptom, not a working-tree loss, so the precise mechanism
could not be reconstructed after the fact, only the fact of the gap.

This session redid the migration for real, using the same primitive
the prior report described (and which two scratch scripts already
sitting in this session's scratchpad, compute_via.py/
apply_via_migration.py, correctly implement): `frob.strata._selfconform
._observed_raw_kinds_by_file` plus `_capability_binding` gives, per
owned file, the normalized capability-kind set `scan_file_capabilities`
observes there. For each via-less `may "ATOM"` on each of the 8
SYS107-flagged nodes, computed the real observing file set (files whose
observed kinds intersect the atom's `expand_declared_kind` set) and
rewrote design/frob.strata's `may "ATOM";` line to
`may "ATOM" via "f1", "f2", ...;`, one node's block at a time
(brace-depth tracked so no other node's declarations were touched).

Migrated 46 may atoms across the 8 target nodes -- same total the prior
(lost) report claimed, this time actually committed
(eb411f43e...HEAD):
  cli 6 atoms, graphlang 4, gates 4, stratamod 4, core 5, vet 7,
  testsuite 11, tickets_ledger 5.
Every atom's observing file set was non-empty (smallest: graphlang's
"sql" and vet's several single-file atoms at 1 file each; largest:
testsuite's fs.write at 249/413 files, exec at 130/413, fs.read at
96/413 -- these remain large surfaces because the capability genuinely
is exercised broadly across the test tree, not because the via list was
left unscoped). No grant had zero observing files, so no SYS101
stale-grant deletion was needed or performed -- every migrated atom
narrowed cleanly to a real via list.

SYS107 before: 8 warnings (cli, graphlang, gates, stratamod, core, vet,
testsuite, tickets_ledger, all "> 20 files, via-less"). SYS107 after: 0
-- `frob check --only sys` now reports 0 errors, 0 warnings from
gate:SELFAUDIT (the "strata header-regex symbol count" WARNING line
present in the raw log is a pre-existing, unrelated informational
mismatch, not a SELFAUDIT/SYS finding).

Evidence (all 3 re-run and passing this session, re-recorded via
`frob ticket evidence`):
  tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
  tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
  tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
`uv run pytest` on the exact 3 node ids: 3 passed.

Gates: `frob check --ticket T-1453 --only sys` clean (0 errors, 0
SELFAUDIT warnings). `frob check --ticket T-1453 --only prework` clean
after `frob ticket sweep T-1453` refreshed the stale sweep. The
`--only scope` SCOPE001/SCOPE002 findings against src/frob/strata/
_selfconform.py and design/frob.strata are PRE-EXISTING (unrelated to
this session's diff, which touched design/frob.strata only) and were
already disclosed in the prior report's own LAND-REPAIR ADDENDUM --
_selfconform.py's broad frob:tests/frob:doc surface predates this
ticket and the concurrent T-1279 lease on src/frob/gates/** still
blocks formally widening scope to cover it; not re-litigated here since
this ticket's own diff this session is design/frob.strata only.
`git diff main --diff-filter=D --stat` is empty (no deletions outside
scope).

Filed: none -- no out-of-scope work discovered this session.

### Changed
```
 design/frob.strata                                 |  98 ++---
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
 src/frob/strata/_selfconform.py                    | 321 ++++++++++++++--
 tests/unit/gates/test_sys_selfaudit.py             |  51 +++
 tests/unit/strata/test_scope_config.py             |  46 +++
 tests/unit/strata/test_selfconform.py              |  68 ++++
 .../unit/strata/test_sys107_via_scope_advisory.py  | 117 ++++++
 tickets.md                                         | 424 ++++++++++++++++++++-
 17 files changed, 1217 insertions(+), 127 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 522 warning(s), 748 waived
- error-findings: AFFECT001@src/frob/strata/_mutation_audit.py
