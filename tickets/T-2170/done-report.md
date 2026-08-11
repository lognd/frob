## Done report

Changed:
- src/frob/tickets/_land.py::land -- calls reclaim_orphaned_squash_residue(root, ticket_id) at the very top of its body, before _land_lock is acquired
- src/frob/tickets/_land_git_ops.py::reclaim_orphaned_squash_residue -- added frob:doc/frob:tests edges (COV001/TEST001), split into _reclaim_via_land_lock_probe + _reset_orphaned_residue_under_lock to clear ARCH103, updated docstring to reflect it is now wired
- docs/design/land-checkpoint-durability.md -- new section cross-referencing the shipped reclaim mechanism (frob:doc anchor target)

Evidence:
- tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup::test_orphaned_residue_from_a_dead_land_is_cleared_before_the_dirtymain_refusal (designated repro; FAILED_AT_PARENT confirmed at 437c06c39, the test-only commit, via --check-repro)
- tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup::test_land_calls_reclaim_before_acquiring_its_own_lock
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_clean_root_is_a_no_op

All 5 pass (5 passed, pytest -o addopts="").

Filed: none

Gates: frob check --only coverage/archgate --ticket T-2170 shows zero findings against reclaim_orphaned_squash_residue/_land_git_ops.py:268 (COV001/TEST001/ARCH103 all cleared -- confirmed by grep against fresh full output). Remaining findings in those gate families are pre-existing, unrelated to this ticket's scope.

### Changed
```
 docs/design/land-checkpoint-durability.md      | 26 +++++++++
 src/frob/tickets/_land.py                      | 22 ++++++++
 src/frob/tickets/_land_git_ops.py              | 76 ++++++++++++++++++--------
 tests/unit/test_land_squash_residue_reclaim.py | 74 +++++++++++++++++++++++++
 tickets/T-2170/ticket.md                       | 27 ++++++++-
 5 files changed, 199 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup::test_orphaned_residue_from_a_dead_land_is_cleared_before_the_dirtymain_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup::test_land_calls_reclaim_before_acquiring_its_own_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_clean_root_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/graph/callgraph.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2170/src/frob/tickets/_land_git_ops.py, PRE001@tickets/T-2170, SELFAUDIT001@design, TEST001@src/frob/graph/callgraph.py, TICK004@tickets.md
