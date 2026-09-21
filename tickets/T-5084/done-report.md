## Done report

T-5084 fixes the measured incident where `.frob/land-status.json`
carried `phase="running"` entries for pids that had exited hours
earlier (T-4562, T-4230: 2-4 hours old) -- indistinguishable, to
anything checking only the entry's PRESENCE, from a genuinely
in-progress land.

Investigation into the ticket's second symptom ("LandInProgress then
refuses ledger writes from ROOT while no land runs") found this is a
SEPARATE mechanism, not actually driven by land-status.json anywhere in
this codebase: `refuse_if_land_in_progress`/`_probe_land_once`
(`frob.tickets._leases`) gate on `tickets.lock`'s own OS-level flock
(T-3612's splice-scoped probe), which already has its own independent
dead-pid handling (the T-1634 orphaned-`land.lock`-reclaim path);
`read_all_leases`'s default reconcile (T-4172) already treats a
terminal ticket's lease as stale. A repo-wide search
(`git grep _read_land_status_entries`) found the ONLY readers of
land-status.json are `frob.tickets._land` itself (write/carry-forward)
and `scripts/fleet_status.py` (a pure DIAGNOSTIC printer that already
does its own live/dead/unknown per-entry classification, T-4266, and
never gates a refusal on it). So the "LandInProgress refuses ledger
writes" clause in the ticket's own Cause text describes a real but
DIFFERENT incident already covered by existing machinery, not a
land-status.json defect; no code changes were made for it, and none
were found to be missing.

Fix (the land-status.json half, the part actually traced to this file):
new `_live_land_status_entries(root)` (`frob/tickets/_land.py`) --
`_read_land_status_entries`'s own raw view, pruned of any entry whose
`pid` is CONFIRMED dead (`pid_alive_tristate(pid) is False`) -- the
always-fresh, read-time "is this land actually in progress" view T-5084
asks for ("prune entries whose pid is gone on every read; treat only
live pids as in progress"). The raw on-disk file is intentionally left
alone: `_write_land_status`/`_prune_dead_land_status_entries`'s own
crash-forensics contract (a dead land's last phase survives until the
`_LAND_STATUS_MAX_ENTRIES` cap forces a rewrite) is unchanged -- this is
a new, additional read-time view, not a change to what gets persisted.
An entry whose liveness is merely ambiguous (`pid_alive_tristate`
returns `None`) is kept, matching this module's existing "cannot
confirm is never dead" posture elsewhere (`_prune_dead_land_status_
entries`'s own docstring).

`frob check --files ... --only gates` continues to hang under this
session's fleet load (confirmed again on this ticket, 100s/300s command
timeouts both exhausted with zero usable output) and is BLOCKED for
that specific command; `ruff check`/`ruff format` and the full touched
test file (`tests/ticket_land_suite/test_land_lock.py`, 27 node ids) all
pass clean, plus a clean `frob ticket land --dry-run`.

### Changed
```
 src/frob/tickets/_land.py                 | 36 ++++++++++++++++++
 tests/ticket_land_suite/test_land_lock.py | 63 +++++++++++++++++++++++++++++++
 tickets/T-5084/ticket.md                  | 22 ++++++++++-
 3 files changed, 120 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_live_entries_drops_confirmed_dead_pids` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_live_entries_keeps_ambiguous_and_alive_pids` (pytest node id, verified passing when recorded)
