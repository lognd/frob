## Done report

Folded in a coordinator-reported live finding of the same bucket-
misclassification class, in the same file, per an explicit mid-task
instruction: `land_process_rows` counted a coordinator's own wait-loop
watcher (`pgrep -f "frob ticket land T-2408"`) as a live land, because
`ps -eo args`'s space-joined text cannot distinguish `ticket`/`land` as
two real, separate argv elements from the same text glued inside one
argv element (the quoted `-f` pattern). Every candidate row is now
re-verified against `/proc/<pid>/cmdline`'s own NUL-delimited argv
(`_pid_has_land_argv_tokens`), dropping a row only on a structural
`False`; a pid that cannot be re-read (already exited, /proc
unavailable) keeps the pre-existing text-only verdict, never treated
as a confirmed false positive.

Both fixes share the root shape T-2475 already names: a bucket a
coordinator acts on (NEEDS CLOSE / LANDS IN FLIGHT) misclassifying an
input that looks like the target but isn't.

### Changed
```
 docs/guides/coordinator-scripts.md     |  52 ++++++++++--
 scripts/fleet_status.py                | 143 ++++++++++++++++++++++++++-------
 tests/unit/test_coordinator_scripts.py | 106 +++++++++++++++++++++++-
 tickets/T-2475/done-report.md          |  40 +++++++++
 tickets/T-2475/ticket.md               |  26 +++++-
 5 files changed, 325 insertions(+), 42 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_story_with_terminal_child_prints_under_blocked_not_needs_close` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandProcessRows::test_watcher_pgrep_pattern_is_not_counted_as_a_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV005@scripts/fleet_status.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
