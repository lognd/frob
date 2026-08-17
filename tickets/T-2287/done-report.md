## Done report

T-2287: `frob ticket reconcile`'s unlanded-branch-work "directive-anchored"
signal (T-1948, `_directive_anchor_signals_on_branch` in
src/frob/tickets/_unlanded.py) matches `frob:ticket T-####` against raw
blob TEXT (`_TICKET_DIRECTIVE_RE`), with no way to tell a real directive
comment apart from a fixture string literal sitting in a test file.
Measured: 239 of 244 real findings were the fixture ids T-9001/T-0104/
T-1/T-draft-9bda8d62, repeated once per branch touching
tests/test_gates.py, tests/test_gates_fix_engine.py, or tests/test_graph.py.

Fix: `_directive_anchor_signals_on_branch` now requires a matched id to
RESOLVE to a real `ticket.md` -- present in `branch_states` (the id's
state on the branch itself) OR `main_states` (the id's state on `main`,
active or archived) -- before treating it as a signal at all. This is
FIX DIRECTION (b) from the ticket body (a narrowing heuristic, not a
real directive-DSL parse; option (a), reusing `frob.graph`'s own comment-
DSL parser, is the stronger fix and is out of this ticket's scope --
noted below as a filed follow-up). `main_states` is threaded down through
`_finished_signals_on_branch` (new required parameter) from the caller
that already computes it once per run (`_unlanded_findings_for_branch`).

Verified against the real repo: `frob ticket reconcile` (dry run) went
from 244 findings across 117 branches to 5 -- exactly the five genuine
ids named in the ticket body (T-1860@t-1860, T-1238@t-2097,
T-1238@t1539-series, T-1238@worktree-agent-a813bca499a672a7b), plus one
transient self-reference from this ticket's OWN worktree branch
(T-1691@t-2287 -- a PRE-EXISTING test fixture in this same file,
test_directive_anchored_code_with_queued_ticket_is_flagged, embeds the
literal string "frob:ticket T-1691" as fixture text, and T-1691 happens
to still be a real, non-terminal ticket on main; disappears once this
worktree lands and its branch is removed, same as any other worktree's
own transient diff). None of T-9001/T-0104/T-1/T-draft-9bda8d62 appear.

Positive controls (tests/unit/test_unlanded_branch_work.py,
TestUnlandedBranchWork):
- test_fixture_directive_string_in_a_test_file_is_not_flagged: a branch
  commits a test file containing a literal "frob:ticket T-9001" string
  (no ticket.md for T-9001 exists anywhere) -- must produce zero findings.
  Confirmed genuinely fails at parent (93852bfae, before the fix):
  AssertionError, one spurious T-9001 finding. Passes after the fix.
- test_genuine_directive_anchored_specimen_still_flagged: must-still-pass
  control -- a REAL directive-anchored specimen (committed non-tickets/**
  file with a live frob:ticket directive, whose ticket.md resolves on the
  branch to a non-in-progress state) is still reported. Uses a
  non-colliding fixture id (T-9401, this file's existing 9xxx-range
  convention for isolated fixtures) so the unit test itself does not
  introduce a new instance of the exact defect it is testing against.

Filed as a follow-up (option (a), out of this ticket's scope): T-2300,
"unlanded-branch directive signal should reuse the real comment-DSL
parser instead of a bare regex" -- reuse `frob.graph`'s real comment-DSL
parser for the directive-anchor signal instead of a bare regex over blob
text, which would also close the residual "commented-out real id" gap
this narrowing fix explicitly does not (T-2287's own body names this
limitation; observed live during this ticket's own work, see above).

Full tests/unit/test_unlanded_branch_work.py (19/19) and
tests/test_ticket_reconcile.py (16/16) pass with the fix.
--designate-repro validated FAILED_AT_PARENT against 93852bfae.

### Changed
```
 src/frob/tickets/_unlanded.py           | 50 ++++++++++++++++++++++++++---
 tests/unit/test_unlanded_branch_work.py | 55 ++++++++++++++++++++++++++++++++
 tickets/T-2287/ticket.md                | 16 +++++++---
 tickets/T-2300/ticket.md      | 56 +++++++++++++++++++++++++++++++++
 4 files changed, 167 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_fixture_directive_string_in_a_test_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_genuine_directive_anchored_specimen_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2287/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2287/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2287/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2287/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2287/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2287, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
