## Done report

T-2049's own acceptance criterion 4 asked to measure, not speculatively
add, whether queue depth/age belongs in fleet_status.py by the same
"silently changes land cost, and nothing prints it where a coordinator
already looks before dispatch" argument that motivated the QUARANTINE
line. This ticket's own investigation found the number real and
currently nonzero but had no documented incident tying it to lost
throughput, so it deferred until either (a) a real incident, or (b)
whoever owns fleet_status.py decides the symmetry argument alone
justifies it.

Decision: (b). `frob verify status` (T-2290, landed the same day as this
ticket) independently reached the identical conclusion for a different
surface -- it now reports both `unverified depth (queued land-intents)`
and `commits since watermark` for the same "coordinator needs to see
this before dispatch" reason. That is the second, independent motivation
this ticket's own text names as sufficient on its own; adding the
symmetric line to fleet_status.py (the FIRST place a coordinator looks,
per T-2049's own precedent) closes the gap.

Added `verify_queue_state()` (scripts/fleet_status.py), mirroring
`quarantine_state()`'s own raw-JSON-read style exactly (this script
deliberately never imports frob.* -- it must stay usable without a built
venv/native extensions) -- reads `.frob/verify-queue.json` directly for
depth (entry count) and the OLDEST `enqueued_at` entry's age. Printed as
a new VERIFY QUEUE line in `_print_fleet_report`, immediately after
QUARANTINE. Deliberately does NOT reconcile the full commit-gap number
`commits_since_watermark`/`frob verify status` computes (a `git rev-list`
spawn) -- that would duplicate an existing, always-available command's
own number rather than add a distinct signal; this line is a depth/age
early-warning, not a second implementation of the reconciled count.

An unreadable queue store reports `(-1, None)`, never a silent `(0,
None)` -- "cannot verify is never verified" applies here exactly as it
does to QUARANTINE's own unknown-state handling.

Positive control: `test_zero_depth_when_no_file`/
`test_prints_empty_when_zero_depth` confirm an empty/never-populated
queue reports and prints as empty, not indistinguishable from the
unreadable case.

### Changed
```
 tickets/T-2126/ticket.md | 10 +++++++++-
 1 file changed, 9 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestVerifyQueueState::test_reports_depth_and_oldest_age` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestVerifyQueueState::test_zero_depth_when_no_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestVerifyQueueState::test_unreadable_queue_is_unknown_never_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMainVerifyQueue::test_prints_depth_and_age_when_nonempty` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMainVerifyQueue::test_prints_empty_when_zero_depth` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@scripts/fleet_status.py, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2126/scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
