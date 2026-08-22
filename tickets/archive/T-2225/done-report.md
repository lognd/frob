## Done report

Added scripts/fleet_status.py::scope_lease_collisions and
_expand_scope_globs_to_paths. `ticket_readiness` now compares a
ticket's own effective scope against every OTHER "live" lease
(reusing T-2222's lease_classification, not re-implemented) at the
RESOLVED-FILE level: both sides' scope globs are expanded against the
real filesystem (pathlib Path.glob, with a bare-trailing-`**` pattern
also tried as `<pattern>/*` since pathlib's own `**` semantics match
directories recursively but not the files inside the deepest one
without a further segment), then intersected as concrete paths -- never
compared as glob TEXT. A collision now surfaces as a SCOPE COLLISION
line naming the holding ticket and the specific colliding file(s), and
gates `dispatchable` to False.

Reproduces T-2225's own measured incident: a ticket scoped to
src/frob/** collides with a live lease scoped literally to
src/frob/tickets/_land.py -- no substring/lexical comparison of those
two strings would ever detect that; expanding both against the real
tree does.

Repro: tests/unit/test_coordinator_scripts.py::
TestTicketReadinessScopeCollision::
test_not_dispatchable_when_scope_files_are_held_by_another_live_lease,
confirmed FAILED_AT_PARENT at 55c79ca78ce34c158bd36b1291e8a2601bc017db
(the repro-only commit -- scope_lease_collisions did not exist on main
at all).

Must-still-pass control:
TestTicketReadinessScopeCollision::test_dispatchable_when_no_colliding_lease
-- a ticket whose scope files are held by no one still reports
dispatchable. Also TestScopeLeaseCollisions::
test_a_reclaimable_lease_is_never_a_collision proves a reclaimable/
root-resident lease (T-2222's own classification) never counts as a
collision even when its scope files genuinely overlap on disk.

### Changed
```
 docs/guides/coordinator-scripts.md     |  39 +++++++-
 scripts/fleet_status.py                | 111 +++++++++++++++++++++-
 tests/unit/test_coordinator_scripts.py | 165 +++++++++++++++++++++++++++++++++
 tickets/T-2225/ticket.md               |  23 +++--
 4 files changed, 323 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestTicketReadinessScopeCollision::test_not_dispatchable_when_scope_files_are_held_by_another_live_lease` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_glob_scope_collides_with_a_literal_lease_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketReadinessScopeCollision::test_dispatchable_when_no_colliding_lease` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_a_reclaimable_lease_is_never_a_collision` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2200-series/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t2200-series/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2225, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
