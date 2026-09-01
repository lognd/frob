## Done report

Added the smallest useful pollable land-status marker (T-2691): `land()`
now writes `<root>/.frob/land-status.json` (`frob.tickets._land._write_
land_status`) at each saga phase -- `acquiring-lock` (before the lock
attempt), `waiting-for-lock` (inside `_land_lock`'s poll loop, with the
holder metadata it is blocked on), `lock-acquired`, `running` (alongside
the existing T-0456 intent-journal write), and `done`/`failed` at the
end -- each write carrying pid, an ISO-8601 UTC `started_at` preserved
across a single land's own phase transitions, and an always-refreshed
`updated_at`. Unlike the T-0456 intent journal, this marker is
deliberately NOT cleared on exit: its last phase plus a stale
`updated_at` next to a `running`/`waiting-for-lock` phase is itself the
"this died mid-flight" signal the 2026-08-20 incident needed. Best-
effort throughout (write failure logged and swallowed, mirroring
`_write_intent`'s posture) -- never able to fail a land itself.

`scripts/fleet_status.py` gained `read_land_status_marker` (best-effort
JSON read of the marker) and `_land_status_marker_line` (its rendering),
wired into `_print_land_status` as a new `LAND STATUS MARKER:` line
printed right after `LANDS IN FLIGHT` -- `_land_status_lines` grew one
new optional trailing parameter (`status_marker_line`, default `None`)
so every pre-existing caller's output is unchanged.

No CLI `frob ticket land-status` verb was added -- the ticket body itself
frames that as a distinct, "future, not-yet-implemented" verb, not
something this ticket's own acceptance asks for; the marker file plus
`fleet_status.py`'s surfacing is the disclosure fix this ticket's own
"smallest useful version" scopes to. `_land_cmd.py` (in scope) needed no
change -- both saga entry points this ticket's incident concerns
(`_land_lock`'s wait loop and `land()`'s own wrapper) live in `_land.py`.

Evidence: `pytest tests/ticket_land_suite/test_land_lock.py::TestLandStatus tests/unit/
test_coordinator_scripts.py::TestReadLandStatusMarker tests/unit/
test_coordinator_scripts.py::TestLandStatusMarkerLine -p no:xdist` -- 8
passed, 0 failed. Also re-ran the full `tests/test_ticket_land.py` suite
(342 tests) to confirm the `_land_lock`/`land()` edits regressed nothing:
342 passed, 0 failed.

Gates: `frob check --ticket T-2691` -- every scope-relevant finding was
resolved: E501/DOC007 (malformed `frob:tests` line-wrap syntax, fixed to
match the file's own `Class.method` convention), AFFECT001 (`land`'s
changed body needed its affects()-closure doc touched --
`docs/modules/tickets-landing.md` new "Pollable land-status marker
(T-2691)" section, added to scope with `--reason`), DOC006 (a broken
doc-anchor link caused by an accidental mid-word wrap), COV001/COV002
(scope extended to both new test files and
`docs/guides/coordinator-scripts.md`, `frob:ticket T-2691` edges added
to every new test method, a new `read_land_status_marker` anchor section
added to the coordinator-scripts guide). Renamed the module constant
`LAND_STATUS_REL` to `_LAND_STATUS_REL` (private, matching `_LAND_LOCK_
REL`'s own convention) since nothing outside `_land.py` needs to import
it -- `fleet_status.py` reads the fixed `.frob/land-status.json` path
directly, the same posture its sibling `/proc`-reading functions already
take toward this module. The remaining 21 `gate:*` errors on the full
`--ticket` run (DEPR006, WAIVE011, DRIFT001 x2, LARGE001 on two unrelated
files, REL001, TICK004 on two unrelated tickets, OPAQUE001 on an
unrelated file, COV003 on T-3410, DOC007/DRIFT002 on an unrelated
`_bisect.py` pair, SELFAUDIT001 on an unrelated test file) are
pre-existing repo-wide findings untouched by this change.

Filed: none -- no out-of-scope work found. (`_land_cmd.py`'s declared
scope went untouched; the incident this ticket fixes lives entirely in
`_land.py`'s own lock/orchestrator code.)

### Changed
```
 tickets/T-2691/ticket.md | 41 ++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 40 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_phase_transitions_are_pollable` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_waiting_phase_records_lock_holder` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_lock.py::TestLandStatus::test_write_failure_is_best_effort_and_never_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestReadLandStatusMarker::test_reads_a_written_marker` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestReadLandStatusMarker::test_missing_marker_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestReadLandStatusMarker::test_unparseable_marker_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandStatusMarkerLine::test_no_marker_renders_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandStatusMarkerLine::test_marker_renders_phase_ticket_and_pid` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 13 error(s), 4224 warning(s), 867 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
