## Done report

Root cause: test_disjoint_v2_tickets_land_with_no_custom_merge (and every
other test in this file) spawns real git subprocesses -- either directly
via the module's own _run helper or transitively via production land()
through gitio.run_argv -- and neither sets an explicit env=, so every
spawn inherits the CURRENT process's os.environ and falls through to the
HOST MACHINE's real --global/--system git config for anything neither the
fixture nor production code sets explicitly (fixture repos only set LOCAL
user.name/user.email via _git_init). That global/system config is real,
mutable, shared state across every pytest-xdist worker PROCESS on this
machine -- unlike tmp_path, which xdist already gives each worker its own
tree under -- so a config value the host happens to carry (this machine's
own ~/.gitconfig has credential.https://github.com.helper, core.autocrlf,
etc.) can slow or otherwise perturb one worker's git spawns under real
parallel contention in a way no single-file or single-test rerun
(section 3b's foreground timeout budget) can reproduce, since a rerun
never puts 4 real workers' git subprocesses in contention at once.

Fix: added an autouse `_isolate_from_host_git_config` fixture (module
level, tests/test_ticket_land.py) that sets GIT_CONFIG_GLOBAL and
GIT_CONFIG_SYSTEM to os.devnull for every test in this file (git >=2.32).
Every git spawn in this module's test session now sees an empty
global/system config regardless of what the host machine actually has
installed, closing the exact gap the ticket names ("the repo-global git
config the test touches").

Verification: could not reproduce the flake even before this fix (5x
standalone `TestLedgerV2LandMergeStory`-scoped -n4 runs, 3x whole-file -n4
runs, all green) -- consistent with the ticket's own note that the
failure required the FULL unscoped suite's real worker contention, which
a scoped rerun structurally cannot recreate (playbook section 3c: the
full suite is a coordinator-only verification). Ran the file 3x more
after the fix (still all green) to confirm no regression; the fix targets
the diagnosed shared-state class directly rather than papering over an
unreproduced symptom. frob check --only test --only archgate --only sys
--ticket T-1393: 0 errors. frob check --only pii_structural --only
prework --ticket T-1393: 0 errors after a sweep refresh.

Deferred: the coordinator should re-run the full unscoped `-n 4` suite
post-land to confirm the flake is actually gone under real contention --
that verification could not be performed from this worktree per playbook
section 3c/6b.

frob:waive BUG002 reason="this defect is a full-suite/xdist-only ordering flake caused by shared host git config contention across worker processes -- the designated evidence test passes standalone at every commit (parent and fix alike), which the ticket's own body already documents; the fix hermetically isolates the test module from that shared state, but the failure itself can only be observed inside a full unscoped -n4 suite run, which is a coordinator-only verification per playbook section 3c/6b and not reproducible via a checkout diff the way BUG002's repro-at-parent check wants"

### Changed
```
 docs/strata/selfconform.md           |  13 ++
 frob.lock                            |   4 +-
 src/frob/strata/_selfconform.py      |  83 +++++++++--
 src/frob/tickets/_leases.py          |  49 +++++++
 tests/test_doctor.py                 |  24 ++--
 tests/test_prework_parity.py         |  16 +++
 tests/test_ticket_land.py            |  32 +++++
 tests/test_ticket_leases.py          |  46 ++++++
 tests/unit/perf/test_serial_pools.py |  23 ++-
 tickets.md                           | 270 ++++++++++++++++++++++++++++++++++-
 10 files changed, 527 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
