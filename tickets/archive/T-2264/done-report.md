## Done report

Lease liveness in lease_staleness_reason's "holder-dead" shape checked
only scan_for_live_worktree_process (is any process cwd'd INSIDE the
lease's worktree). frob ticket land is invoked --worktree <path>, and
root resolves to the primary checkout (T-1003) -- so when a land runs
FROM the root, none of its own processes are ever cwd'd inside the
worktree it is landing, and a genuinely live land (real, climbing CPU
time, 454s elapsed in the measured incident) read reclaimable.

CORRECTED FRAMING (per the coordinator's own follow-up measurement,
which supersedes the ticket body's original text): lands do NOT always
run from the root. T-2231's land ran from INSIDE its own worktree and
correctly read [live]; T-2254's ran from the root and read
[reclaimable]. Both shapes occur in practice depending on where the
invoking agent's shell cwd was -- the fix must cover the root-invoked
case as an ADDITIONAL signal, never assume it is the only shape (which
is exactly what _land_in_progress_for_ticket does: it is layered
alongside scan_for_live_worktree_process, which already correctly
covers the in-worktree-invocation shape).

INDEPENDENTLY VERIFIED the coordinator's second, inverse-direction
observation: ran `uv run python scripts/fleet_status.py` myself and
saw `T-2264 -> t-2264 [reclaimable]` while 0 lands were in flight and
this ticket's own lease was actively held by me (mid-session) -- the
classifier is wrong in both directions, not just the one the ticket
describes. This confirms fleet_status.py carries its OWN separate bug
beyond the one this ticket fixes in _leases.py -- most likely its own
duplicated classifier does not gate on the lease's own TTL/in-progress
state the way lease_staleness_reason's "holder-dead" shape does
(_leases.py never misclassifies a fresh, non-TTL-expired lease as
holder-dead regardless of the process scan -- see the "ticket-terminal
checked before holder-dead, never gated the same way" contract in
lease_staleness_reason's own docstring). Filed as scope-note evidence
for whoever picks up fleet_status.py's T-2229-series follow-on; not
fixed here since scripts/fleet_status.py is under T-2229's live lease
and out of this ticket's declared scope.

Fix: _land_in_progress_for_ticket (src/frob/tickets/_leases.py) adds
this as an ADDITIONAL liveness source layered onto (never replacing)
scan_for_live_worktree_process. Two structured (never text-matched)
signals, the SAME dual check refuse_if_land_in_progress/
_probe_land_once already use for a different caller: (1) land.lock's
own recorded holder metadata (ticket_id), confirmed live via the same
non-blocking flock probe _land_flock_probe already uses -- a dead
holder's flock is released by the kernel the instant it exits, so no
separate pid-liveness check is needed, and frob ticket land serializes
on a SINGLE root-level land.lock so matching a lease's own ticket_id
against the CURRENT holder is an exact match, not a heuristic; (2)
_scan_for_live_land_process's /proc argv+cwd belt-and-braces backstop
for the narrow window before a land has written its own holder
metadata. Both parse /proc's own structured per-pid files (NUL-split
cmdline, cwd readlink) and match discrete argv tokens against a fixed
grammar -- never a substring search across a concatenated ps line.

MUST-STILL-PASS verified directly: test_holder_dead (a genuinely dead
holder, no land, no cwd process) and
test_in_progress_lease_on_a_live_worktree_is_not_stale (a live
in-worktree agent) both still pass unchanged -- the new check is
appended with `and`, short-circuited before it ever runs when the
existing checks already decide the outcome.

Two-consumer consistency (acceptance 3): _leases.py is the
authoritative, dangerous copy (backs `release-lease`) and is fixed
here. scripts/fleet_status.py's own reclaimable classifier (its L266
cwd scan, T-2222) needs the equivalent join against ITS OWN already-
computed land_invocations()/land_lock_holder_pids() before it will
agree with this fix -- it cannot import frob (deliberate no-import
contract), so this is NOT a shared function; it is a PARITY SPEC: any
lease whose ticket_id names the CURRENT land.lock holder (matching
this file's _read_land_lock_holder_json shape) or matches a live
land_invocations() entry must not display [reclaimable]. Documented in
the fix commit's own message for the T-2229 series to pick up
mechanically -- not fixed here, since scripts/fleet_status.py is under
T-2229's live lease and explicitly out of this ticket's scope.

Repro-first: the failing test was committed alone (fed355058) and
verified FAILED_AT_PARENT against it before the fix commit (75da45e51)
was added on top -- frob ticket evidence --check-repro --base-ref
fed355058 confirms FAILED_AT_PARENT.

### Changed
```
 src/frob/tickets/_leases.py | 74 +++++++++++++++++++++++++++++++++---
 tests/test_ticket_leases.py | 91 +++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2264/ticket.md    | 30 ++++++++++++---
 3 files changed, 184 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestLeaseStalenessReason::test_land_shields_lease` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLeaseStalenessReason::test_holder_dead` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLeaseStalenessReason::test_in_progress_lease_on_a_live_worktree_is_not_stale` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLeaseStalenessReason::test_other_land_no_shield` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2264/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2264/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
