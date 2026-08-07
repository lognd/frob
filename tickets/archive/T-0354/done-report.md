## Done report

Delegated app/ticket_runner.py's _run_sweep to frob.gates.sweep_ticket
instead of carrying its own copy of the xref loop (T-0236's flagged
follow-up). The old copy had the same two bugs T-0240 fixed in
gates/_prework.py::sweep_ticket: an unbounded xref(symbol, root) re-walk
of the whole tree per scope pattern (ignoring the scan_path it computed),
and a Path(pattern).stem guess feeding raw glob syntax into xref as a
symbol name. src/frob/app/** was out of T-0240's scope, so this sibling
copy kept both bugs live. Removed the duplicate _xref_hits_for_scope and
_scope_digest_for_ticket helpers entirely; _run_sweep now calls
sweep_ticket(root, ticket) directly, so the two call sites can no longer
desync.

### Changed
```
 src/frob/app/ticket_runner.py | 73 +++++++++++++------------------------------
 tickets.md                    | 30 ++++++++++++++++--
 2 files changed, 49 insertions(+), 54 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_foreground_runs_sweep_synchronously` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_spawns_detached_sweep_subprocess` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_popen_failure_falls_back_to_synchronous_sweep` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_exec_kill_switch_forces_synchronous_sweep` (pytest node id, verified passing when recorded)
