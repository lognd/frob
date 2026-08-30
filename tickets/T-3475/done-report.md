## Done report

Triaged both new EXHAUST002 findings. scripts/fleet_status.py::_true_flock_holder_pid: real fix, next(iter(matches)) -> next(iter(matches), None), making the call provably safe (len(matches)==1 was already checked but is invisible to the resolver); finding gone entirely, not waived. src/frob/tickets/_new_renumber.py::_open_and_lock_counter_file: TicketLockUnavailable is the function's own documented deliberate fail-closed raise (T-2952), meant to propagate uncaught; added a reasoned frob:waive EXHAUST002. Both changes are frob:no-behavior-change. Evidence: tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid 4/4 pass. frob check --only exhaustive_handling before/after confirms the fleet_status finding disappears and the renumber finding shows waived (waived count 113 -> 114). frob check --only lint clean on both touched files. No new tickets filed.

### Changed
```
 scripts/fleet_status.py           |  8 +++++++-
 src/frob/tickets/_new_renumber.py |  1 +
 tickets/T-3475/done-report.md     | 17 +++++++++++++++++
 3 files changed, 25 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_finds_the_true_holder` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_ignores_a_lock_on_a_different_inode` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_unreadable_proc_locks_is_indeterminate` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_missing_lock_file_is_true_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 10 error(s), 4039 warning(s), 869 waived
- error-findings: AFFECT001@scripts/fleet_status.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
