---
id: T-2196
title: 'fleet_status --ticket prints ''ticket does not exist on main'' and then reports
  dispatchable: True on the next line, so the pre-dispatch check endorses dispatching
  a nonexistent ticket'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: repro + regression tests for the dispatchable-verdict fix (nonexistent-ticket
    and blocked_by cases)
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_blocker_is_still_open
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_every_blocker_is_done
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
- tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main
acceptance:
- text: 'Reproduced verbatim: ''python3 scripts/fleet_status.py --ticket T-2195''
    printed ''main: ticket does not exist on main'' and then ''dispatchable: True''
    on the very next line, while a real leased ticket (T-2183) correctly printed ''dispatchable:
    False''. So the verdict is computed from lease state alone and ignores the existence
    fact it just measured and displayed. The coordinator dispatched a nonexistent
    ticket to an agent; this check would have endorsed it. This test MUST fail against
    current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main
- text: dispatchable must be FALSE whenever the ticket does not exist on main, and
    the reason must be stated in the same terms as the measured fact -- do NOT print
    a bare False. Derive it from the ledger read that already happens (the code clearly
    performs it, since it prints the nonexistence), not from a second lookup that
    could disagree with the first.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
  - tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by
- text: 'Audit every other input to the dispatchable verdict for the same shape: a
    fact measured, displayed, and then omitted from the decision. At minimum check
    terminal state (a done/dropped ticket is not dispatchable), blocked_by edges (a
    blocked ticket is not dispatchable), and SCOPE DIVERGES. Do NOT fix only the nonexistence
    case -- the defect class is ''the report knows more than the verdict uses'', and
    fixing one instance leaves the rest.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_blocker_is_still_open
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_every_blocker_is_done
  - tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
  - tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Reproduced verbatim: `ticket_readiness()` computed `state_on_main =
None` when the ticket does not exist on main, and `None not in ("done",
"dropped", "in-progress")` is vacuously True -- so the verdict read
`dispatchable: True` right below a printed `main: ticket does not exist
on main` line. Repro committed alone (tests/unit/test_coordinator_
scripts.py), observed FAILING against unfixed fleet_status.py --
`frob ticket evidence --check-repro` confirms FAILED_AT_PARENT at
220e04a2a.

Fix: `dispatchable` now requires `main_info is not None` explicitly.
Audited every other measured-but-possibly-unused fact per acceptance
[2]:
- terminal state: already checked (done/dropped/in-progress), unchanged.
- blocked_by edges: NEVER checked before this ticket. `ticket_
  frontmatter_on_main` now also parses `blocked_by:` (previously it read
  only state/scope), and a new `_open_blocker_ids` helper + `open_
  blockers` field gate `dispatchable` on whether any cited blocker is
  still open on main.
- SCOPE DIVERGES: was computed (`scope_diverges`) and printed, but never
  factored into `dispatchable` -- only reachable when a live lease
  exists, which already forces `dispatchable=False` today, but now
  explicitly gates the verdict too rather than relying on that
  transitive implication holding forever.

Manually confirmed live against this repo: `python3 scripts/
fleet_status.py --ticket T-9999999` now prints `dispatchable: False`
right under `main: ticket does not exist on main`.

Evidence:
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main (designated repro, FAILED_AT_PARENT confirmed at 220e04a2a)
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_blocker_is_still_open
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_every_blocker_is_done
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main (regression, still green)
- tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by

Filed: none.

Gates: full `tests/unit/test_coordinator_scripts.py` suite: 74 passed,
0 failed (SUITE-RESULT collected=74 failed=0).

### Changed
```
 scripts/fleet_status.py                | 147 ++++++++++++++++++++++++---------
 tests/unit/test_coordinator_scripts.py | 112 +++++++++++++++++++++++++
 tickets/T-2196/ticket.md               |  31 +++++--
 3 files changed, 247 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_ticket_does_not_exist_on_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_blocker_is_still_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_every_blocker_is_done` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_blocked_by` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@scripts/fleet_status.py, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV005@scripts/fleet_status.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2196, SELFAUDIT001@design, TEST010@tests/test_lang.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
