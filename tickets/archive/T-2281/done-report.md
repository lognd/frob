## Done report

Changed:
  scripts/fleet_status.py::scope_lease_collisions (new land_ticket_ids param)
  scripts/fleet_status.py::_land_ticket_collisions (new, ARCH001 split)
  scripts/fleet_status.py::ticket_readiness (passes land_invocations() in)
  docs/guides/coordinator-scripts.md (new/updated entries)

Corrected framing per the coordinator's own two-message correction on
this ticket during the session: earlier guidance suspected a TTL/
in-progress gating defect in the classifier; that was investigated by a
different agent (T-2271/T-2264) and found to be a real, transient,
INTENTIONAL window (a land's local worktree close releases the shared
lease immediately, before the squash reaches main) -- not a bug. T-2281
is narrower and real: T-2225's scope-collision check reads ONLY leases()
to decide occupancy, so it is blind to exactly that window -- a ticket
whose land is actively running holds no lease, yet its scope files are
genuinely still contended.

Fix mirrors T-2264's own _land_in_progress_for_ticket shape (src/frob/
tickets/_leases.py) but does not import it (fleet_status.py has no frob
import by design) -- instead JOINS fleet_status's own already-computed
land_invocations() (ticket ids of live, structurally-parsed `ps -eo
pid,ppid,time,args` rows matching a real land invocation, never text-
grepped) into scope_lease_collisions as a second, independent occupancy
source. Each such ticket's scope is read from main (no lease exists to
read it from during this window) via ticket_frontmatter_on_main. Never
inferred from ticket STATE (in-progress on main during this window is
normal and intentional, T-2271's own explicit finding) -- only from a
live land process actually naming the ticket. A ticket already reported
via a live lease is never double-counted.

Did NOT touch lease_classification/_leases.py at all (T-2264 owns that
file and has its own unlanded work there, per the coordinator's explicit
instruction) -- this stays entirely inside scope_lease_collisions'
existing responsibility.

Evidence: tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_land_in_progress_ticket_with_no_lease_still_collides
  FAILED_AT_PARENT confirmed at 057071d26 (repro-only commit); PASSED
  after the fix commit 1b2b929c7.
  Also added: test_land_ticket_disjoint_scope_is_not_a_collision (must-
  still-pass: a land-in-flight ticket with no scope overlap is not a
  collision), test_land_ticket_id_matching_a_live_lease_is_not_double_
  reported, test_the_ticket_s_own_id_in_land_ticket_ids_is_never_self_
  collision (never self-collides). Fixed test isolation on two existing
  TestTicketReadinessScopeCollision tests that did not monkeypatch
  land_invocations (previously called the real one, silently correct by
  luck; now deterministic).
  Full run: tests/unit/test_coordinator_scripts.py -- 112 collected, 0
  failed.

Filed: none

Gates: frob check --ticket T-2281 -- gate:SCOPE/gate:PREWORK clean;
  gate:AFFECT closed via real doc edits; the ARCH001 finding this diff
  introduced on scope_lease_collisions was fixed by extracting
  _land_ticket_collisions (real duplication reduction, mirrors T-2213/
  T-2229's own split precedent in this file), not waived; frob:tests
  edges added for both functions.

### Changed
```
 docs/guides/coordinator-scripts.md     | 23 +++++++++
 scripts/fleet_status.py                | 64 ++++++++++++++++++++++++-
 tests/unit/test_coordinator_scripts.py | 88 ++++++++++++++++++++++++++++++++++
 tickets/T-2281/ticket.md               | 22 ++++++++-
 4 files changed, 193 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_land_in_progress_ticket_with_no_lease_still_collides` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2281/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2281/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2281/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2281/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2281/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
