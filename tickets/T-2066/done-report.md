## Done report

Fixed `OrphanedEvidenceDeletion` misattributing a pre-existing, dropped-
ticket evidence deletion to an unrelated landing branch.

Root cause: `_orphaned_evidence_findings` (src/frob/tickets/_land.py) had
no special case for a `dropped` ticket -- its evidence citations were
checked as if they were live proof obligations, the same as a `queued`/
`in-progress`/`done` ticket's. T-1579's own Done report documents that
its escape mechanism was implemented once, found unsound, and reverted
(commit 7597ba37a), which deleted the test node T-1579's evidence cited
-- expected and intentional, since T-1579 is `dropped` ("the work as
specified should NOT be done"). T-1959's land, an entirely unrelated
ticket that only ever touches `TestDeadSymbolGate` in the same file,
still got refused over T-1579's stale citation: the node-level narrowing
`_test_node_existed_at_ref` added by T-2060 checks presence at the
landing branch's merge-base, which does not by itself distinguish "this
branch's own diff removed the node" from "the node was already gone via
an earlier, unrelated main-side change the branch's fork point still
predates" -- exactly what happens when a worktree's fork point is older
than the commit that did the (intentional, dropped-ticket-only) deletion.

Fix: `_orphaned_evidence_findings` now skips any `other.state is
TicketState.DROPPED` ticket outright, before any node-granularity check
runs at all -- a dropped ticket's evidence is a historical record of a
decision that was tried, found unsound, and abandoned, never a live
"this test must keep resolving" obligation a DIFFERENT ticket's land
should ever be gated on. A still-open or `done` sibling ticket in the
exact same shape is completely unaffected and still refuses exactly as
before (verified directly: `test_a_genuine_this_branch_deletion_still_
refuses`, unmodified, still passes).

Positive control, tests/unit/test_land_orphaned_evidence_node_
granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::
test_dropped_tickets_evidence_never_orphans_a_land -- constructs the
T-1959/T-1579 incident's exact shape (a node that existed at the landing
branch's own merge-base, so the T-2060 node-level narrowing alone would
still flag it) against a DROPPED other-ticket, and asserts it never
orphans the land. Confirmed via `frob ticket evidence --check-repro`
that this test genuinely fails against the pre-fix code (commit
d354580af) and passes after the fix.

Full tests/unit/test_land_orphaned_evidence_node_granularity.py (9
tests) and tests/test_ticket_land.py (285 tests) pass.

### Changed
```
 src/frob/tickets/_land.py                          | 20 ++++++++-
 ...test_land_orphaned_evidence_node_granularity.py | 49 +++++++++++++++++++++-
 tickets/T-2066/ticket.md                           | 21 +++++++++-
 3 files changed, 85 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_dropped_tickets_evidence_never_orphans_a_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_a_genuine_this_branch_deletion_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_node_level_narrowing_clears_a_pre_existing_absence` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH001@src/frob/tickets/_land.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2066/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2066/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2066/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2066/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2066/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2066, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
