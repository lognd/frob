---
id: T-2225
title: fleet_status --ticket reports dispatchable=True when the ticket's SCOPE FILES
  are held by another agent's live lease (two mis-dispatches measured)
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
blocked_by:
- T-2222
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestTicketReadinessScopeCollision::test_not_dispatchable_when_scope_files_are_held_by_another_live_lease
- tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_glob_scope_collides_with_a_literal_lease_file
- tests/unit/test_coordinator_scripts.py::TestTicketReadinessScopeCollision::test_dispatchable_when_no_colliding_lease
- tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_a_reclaimable_lease_is_never_a_collision
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestTicketReadinessScopeCollision::test_not_dispatchable_when_scope_files_are_held_by_another_live_lease
acceptance:
- text: '--ticket on a ticket whose scope files are held by another live lease reports
    the collision and names the holding ticket (fails today: prints lease=none, dispatchable=True)'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadinessScopeCollision::test_not_dispatchable_when_scope_files_are_held_by_another_live_lease
- text: A glob scope entry colliding only after expansion is detected (src/frob/**
    vs a live lease on src/frob/tickets/_land.py) -- resolved paths, never string
    comparison
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_glob_scope_collides_with_a_literal_lease_file
- text: A ticket with no colliding lease MUST STILL report dispatchable (must-still-pass
    control against flagging everything)
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadinessScopeCollision::test_dispatchable_when_no_colliding_lease
- text: A reclaimable or residual lease does not count as a collision -- reuse T-2222's
    classification, do not re-implement it
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions::test_a_reclaimable_lease_is_never_a_collision
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# `fleet_status --ticket` reports "dispatchable: True" for a ticket whose scope files are held by another agent's live lease

## Measured evidence (2026-08-16)

Dispatched T-2217 and T-2220 to an agent. Both were immediately unworkable:

- **T-2217** needs `src/frob/app/config.py` -> `ScopeLeaseConflict`, held by a
  LIVE T-2221 lease (`.claude/worktrees/t-2221`, real commits, not stale).
- **T-2220** needs `src/frob/tickets/_land.py` -> `frob ticket work` refused,
  held by a LIVE T-2215 lease. That is the exact function region
  (`merge_commit`, `_land.py:1383-1384`) the fix must edit, so this is a real
  content collision, not merely a ledger one.

The pre-dispatch readiness check reported, for both:

    lease: none
    dispatchable: True

Which is TRUE as written and useless as advice. It answers "does this ticket
hold a lease?" -- the question a coordinator asks is "can an agent start this
right now?" Those differ exactly when another ticket leases the files.

The agent burned a full startup, a premise check, and two refused
`scope`/`work` attempts before reporting back, on two tickets that could not
have been started. That is the cost per mis-dispatch.

## Why the existing tooling did not prevent it

`frob ticket wave --agents N` exists and groups scope-disjoint tickets. The
operating notes already say to use it. It was not used -- so the rule exists
and did not fire. Per the standing audit duty, a rule that was not followed is
not the fix; the check must live where the dispatch decision is actually made,
which is `fleet_status --ticket`.

## Do NOT fix it this way

- **Do NOT tell the coordinator to remember `frob ticket wave`.** That is the
  rule that already failed. The readiness command must answer the question.
- **Do NOT compare scopes as strings.** Scope entries are globs
  (`src/frob/**`); a live lease on `src/frob/tickets/_land.py` collides with
  it, and no substring comparison of those two texts reports that. Expand
  globs and compare resolved PATHS. Standing directive: token/grammar, never
  lexical.
- **Do NOT key the collision on the ticket id or the worktree directory
  NAME.** A series agent works several tickets from ONE worktree, so
  `T-2203`'s lease legitimately pointed at `t2201-series`. Read each lease
  record's own fields.
- **Do NOT make it refuse or auto-release.** This is a REPORTING fix. The
  authoritative refusal already exists and works correctly -- `frob ticket
  work` and `frob ticket scope` both refused properly here. This only surfaces
  that verdict BEFORE an agent is spawned instead of after.

## Acceptance criteria

1. (MUST FAIL FIRST) `--ticket T-####` on a ticket whose scope files are held
   by another ticket's live lease reports the collision and names the holding
   ticket. Fails today: it prints `lease: none` / `dispatchable: True`.
   Confirm `--check-repro` reads FAILED_AT_PARENT before the fix commit.
2. A glob scope entry that collides only after expansion is detected -- e.g.
   scope `src/frob/**` vs a live lease on `src/frob/tickets/_land.py`.
3. A ticket with NO colliding lease MUST STILL report dispatchable
   (must-still-pass control). A change that flags everything as colliding
   would satisfy 1-2 and stop all dispatch.
4. A lease that is itself reclaimable/residual does NOT count as a collision
   (this is why it is blocked_by T-2222, which establishes live-vs-reclaimable
   classification -- reuse that, do not re-implement it).

## Scope note

Blocked on T-2222 deliberately: both edit `scripts/fleet_status.py`, and
T-2222 builds the live-vs-reclaimable lease classification this needs. Filing
them as concurrent tickets would reproduce the exact collision this ticket is
about.

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
