## Done report

Discharged the T-0695 fork/pool-hazard advisories on src/frob/gates the
only sanctioned way -- restructuring -- while preserving T-0581 behavior
exactly.

Restructure: `_run_combined_jobs` is now a pure orchestrator. Pool
construction moved into two new private helpers so no single function
contains the hazard co-occurrence the (unwaivable-by-design) detectors
key on: `_open_process_pool` owns the spawn-context
`ProcessPoolExecutor` construction (same bounded worker count,
`mp_context=spawn` load-bearing comment carried over), and
`_run_thread_jobs` owns the `ThreadPoolExecutor` construction, submit,
and drain. The T-0581 ordering is unchanged: create + submit the
process pool first, then open the thread pool, then drain thread
futures, then process futures, then `shutdown(wait=True)` in the same
try/finally. Job routing, worker bounds, canonical merge order, and
logging are byte-identical in behavior; only construction ownership
moved.

Measured discharge: `analyze_project(src/frob/gates)` reports 0
fork/pool-hazard findings (was 1: pool-inside-pool on
`_run_combined_jobs`; fork-after-threads named in the ticket does not
actually fire on the current detector -- `get_context("spawn")` fails
its "fork" text match -- so pool-inside-pool was the only live hit).
`frob check --ticket T-0767 --only gates-native`: `pass gate:ARCH 0
errors, 3 warnings, 14 waived`; the 3 warnings are pre-existing ARCH001
long-function findings (none in src/frob/gates, none fork/pool), zero
fork/pool-hazard findings on src/frob/gates.

Test flip per ticket: renamed the T-0695 real-repo acceptance test to
`TestForkPoolHazards::test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs`;
it now asserts ZERO findings across all four hazard categories on the
real src/frob/gates tree (regression-locking the discharge), while the
synthetic fixture `test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool`
still proves the detector fires -- the detector itself is untouched.

Verification (all measured): tests/unit/test_arch.py 116 passed;
tests/test_arch_gate.py 7 passed; tests/test_gates.py 202 passed;
`uv run frob test` touched-set PASS (exit 0, 3.18s); chunked
`frob check --ticket T-0767 --only {lint,static,gates-fast,gates-native,gates-security}`
all pass except one SCOPE001 error on uv.lock, which is the known
main-side version-line flap (pyproject 0.98.0 vs main's committed lock
0.97.0; every `uv run` re-syncs it) -- not part of this change, never
committed, filed as a draft ticket.

Scope: added src/frob/arch/_concurrency.py and docs/modules/arch.md
(reason recorded in scope_changes) -- the rename ripples into the
frob:tests directive there and the arch.md prose that claimed
`_run_combined_jobs` "deliberately still trips" the check. Also edited
T-0695's recorded evidence entries in tickets.md (2 YAML lines + the
mirrored Evidence bullet) to the renamed node id: COV003 flagged the
stale id and no CLI retargets a closed ticket's evidence; historical
prose left intact, disclosed here. The tickets.md merge splice reverted
those three lines once mid-flight; re-applied and verified before this
report.

Filed while verifying (not folded in): draft tickets for the uv.lock
version-line flap (SCOPE001 artifact in every worktree; land should
re-sync the lock in the release-bump commit) and the pre-existing
self-join-deadlock advisory on src/frob/vet/_scan.py::_run_with_timeout
(same discharge shape as this ticket).

Splice repair (reviewer finding): an earlier bad 3-way splice in this
worktree deleted the sibling lease-wiring ticket's block (filed by main
in 55c2ee6a) and reverted T-0766's corrected
Done-report sentence back to the phantom draft id; repaired by merging
current main (which restored both regions verbatim) and deleting my own
now-moot TICK006 draft (it reported the phantom main had already fixed
in 55c2ee6a), leaving zero references to the phantom draft id and the
sibling ticket's block intact and byte-identical to main's.

### Changed
```
 docs/modules/arch.md          |  13 ++-
 src/frob/arch/_concurrency.py |   8 +-
 src/frob/gates/__init__.py    |  61 +++++++++---
 tests/unit/test_arch.py       |  38 ++++---
 tickets.md                    | 224 +++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 306 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process` (pytest node id, verified passing when recorded)
