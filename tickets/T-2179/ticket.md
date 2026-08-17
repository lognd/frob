---
id: T-2179
title: fleet_status.py::worktrees_touching_ticket reports ledger-only churn as 'already
  implemented' (T-2172 follow-up)
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: tests + doc anchors for the scope-aware worktrees_touching_ticket fix
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: tests + doc anchors for the scope-aware worktrees_touching_ticket fix
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ledger_only_churn_is_not_reported
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_scope_globs_never_reports
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_when_nothing_touches_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found by the coordinator using `--ticket` (T-2172's own new flag) for real
dispatch decisions: `worktrees_touching_ticket` reports ANY worktree branch
with an unlanded commit touching `tickets/<id>/` as "already implemented",
with no distinction between:

- a branch that touched files in the ticket's own declared SCOPE (genuine
  implementation work -- should report loudly)
- a branch that touched ONLY `tickets/<id>/**` itself (a ledger-only edit --
  id-collision renumbering churn, a scope narrowing, a Done report commit
  on a ticket that was later abandoned/renumbered away -- not implementation
  at all)

Real incident: `--ticket T-2114` printed `ALREADY IMPLEMENTED on: t-2071,
t-2099, t-2105, t-2107, t-2109, t-2110, t2049-series` -- seven branches, none
of which actually implemented T-2114. T-2114 briefly collided with a
different ticket id before being renumbered to T-2140; every one of those
branches touched `tickets/T-2114/ticket.md` during that collision-recovery
churn, never the ticket's own declared scope. A coordinator trusting this
line would skip real work believing it was already done -- worse than
printing nothing, since a false "already implemented" is exactly the kind
of wrong answer that gets trusted without re-checking.

Fix: `worktrees_touching_ticket` (or `ticket_readiness`, whichever owns the
distinction) should only report a worktree as "already implemented" when
its unlanded commits touch a file matching the ticket's OWN declared scope
globs (from `ticket_frontmatter_on_main`, same source `ticket_readiness`
already reads) -- not merely `tickets/<id>/**`. A branch that touched only
the ticket's own ledger path should report as ledger-only (or not at all),
never as implementation evidence.

Filed as a follow-up to T-2172 per the coordinator's explicit instruction,
not folded into T-2167/T-2171/T-2174 (a distinct defect in a tool
coordinators now rely on for real dispatch decisions).

## Done report

Changed:
- scripts/fleet_status.py::_matches_any_scope_glob (new) -- `fnmatch`-based
  glob match, the same semantics `frob ticket scope`'s own globs use.
- scripts/fleet_status.py::worktrees_touching_ticket -- now takes a
  `scope_globs` argument and requires BOTH a `tickets/<id>/`-touching
  commit AND a scope-glob match somewhere in the branch's full `main...
  HEAD` diff before reporting a worktree as "already implemented". An
  empty `scope_globs` always reports empty (never falls back to the old
  looser behavior).
- scripts/fleet_status.py::ticket_readiness -- passes the LIVE lease's
  scope (if a lease is held) or `main`'s declared scope to
  `worktrees_touching_ticket`, mirroring the "trust the lease, not the
  ticket file" rule `scope_diverges` already established.
- docs/guides/coordinator-scripts.md -- new `_matches_any_scope_glob`
  section, rewritten `worktrees_touching_ticket` section documenting the
  T-2172 follow-up incident and the fix.
- tests/unit/test_coordinator_scripts.py -- 2 new tests
  (test_ledger_only_churn_is_not_reported reproducing the exact T-2114
  false-positive shape, test_empty_scope_globs_never_reports), updated
  the 3 existing `worktrees_touching_ticket`/`ticket_readiness` call sites
  for the new two-arg signature.

Evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ledger_only_churn_is_not_reported
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_scope_globs_never_reports
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_when_nothing_touches_it
- `uv run pytest tests/unit/test_coordinator_scripts.py -o addopts="" -q`:
  50 passed (was 48 before this ticket's 2 new tests).
- Manually reproduced the coordinator's own report with a stubbed
  three-arg `_git`: `worktrees_touching_ticket("T-2114", [])` (no known
  scope) returns `[]`; with the OLD single-condition logic that same
  input would have returned every worktree with a `tickets/T-2114/`-
  touching commit, exactly the seven-branch false positive reported.
- `uv run frob check --land-parity`: 7 unscoped errors remain, all
  pre-existing debt from T-2157 (`ARCH103`/`COV001`/`TEST001` on
  `reclaim_orphaned_squash_residue`, already disposed to T-2170 per the
  coordinator) plus the standing `_land_cmd.py` ARCH001/DRIFT001 and
  `TICK004` on T-0969 -- none touch `scripts/fleet_status.py`,
  `tests/unit/test_coordinator_scripts.py`, or
  `docs/guides/coordinator-scripts.md`.

Filed: none new.

Gates: clean of any finding in this ticket's own files; remaining
`--land-parity` errors confirmed pre-existing and outside scope by file
path.

### Changed
```
 docs/guides/coordinator-scripts.md     | 33 +++++++++---
 docs/modules/graph.md                  | 47 +++++++++++++++++
 rapid-debt.jsonl                       |  1 +
 scripts/fleet_status.py                | 93 +++++++++++++++++++++++++++-------
 src/frob/graph/callgraph.py            | 73 +++++++-------------------
 tests/unit/test_coordinator_scripts.py | 84 ++++++++++++++++++++++++++----
 tickets/T-2171/ticket.md               |  7 ++-
 tickets/T-2174/ticket.md               |  6 ++-
 tickets/T-2179/ticket.md     | 74 +++++++++++++++++++++++++++
 9 files changed, 325 insertions(+), 93 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ledger_only_churn_is_not_reported` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_scope_globs_never_reports` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_when_nothing_touches_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_land_git_ops.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2179, SELFAUDIT001@design, TEST001@src/frob/tickets/_land_git_ops.py, TICK004@tickets.md
