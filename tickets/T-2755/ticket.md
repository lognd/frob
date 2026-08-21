---
id: T-2755
title: worktree_content_classification's ticket_id resolution keys on t-<id> worktree
  naming, same class as T-2747
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: AFFECT001 doc closure plus this ticket's own test additions
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: AFFECT001 doc closure plus this ticket's own test additions
  actor: logan
  at: '2026-08-21'
evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicketIds::test_non_conventionally_named_worktree_resolves
- tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicketIds::test_no_start_transition_commits_resolves_empty
- tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicketIds::test_series_worktree_resolves_every_started_id
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_non_conventionally_named_worktree_classifies_active_via_structural_ids
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_worktree_with_genuinely_no_ticket_is_not_force_matched
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1baac70c39c519a4360f78b518820e50de5602f0
---
`worktree_content_classification` (`scripts/fleet_status.py`, the
`WORKTREES` section's STRANDED/STALE/ACTIVE verdict) resolves a worktree's
owning ticket the same way the leases-section leak detector used to,
before T-2747: via `_worktree_ticket_id(path.name)`, `True` only for a
literal `t-<id>` directory name.

Found while reviewing fleet_status.py's other verdicts for the same
naming-assumption class, per T-2747's own broader ask.

Concretely: `worktree_content_classification(path, ticket_id=...)` only
gets a non-`None` `ticket_id` argument from its one caller
(`_print_worktrees_section`) via this same `_worktree_ticket_id(name)`
resolution. For a subject-named worktree (`waive-liveness`) or a series
worktree holding a sibling ticket under another ticket's name
(`t2738-t2737` holding T-2737), `ticket_id` resolves to `None` and the
function's own ticket-state ACTIVE short-circuit (the block that reads
`ticket_frontmatter_on_main(ticket_id)` and returns `"ACTIVE", []` for
any non-terminal state) never fires -- the worktree instead falls
straight through to the raw content diff test
(`_is_deletion_dominant`/`_lines_absent_from_main`).

This is a real, structurally identical instance of the exact defect
T-2747 fixed for leases: a genuinely in-progress worktree can misreport
as STRANDED or STALE in the `WORKTREES` section purely because of its
directory name, not its actual state. Lower severity than T-2747's own
leak-detector bug (this section is report-only -- nothing auto-deletes
off a STRANDED verdict, `frob worktree sweep` remains the gated removal
path per `worktree_content_classification`'s own docstring), but it is
the same false signal shape an operator could act on by hand.

Fix shape: replace `_worktree_ticket_id(path.name)` in
`_print_worktrees_section` (or wherever `ticket_id` gets threaded into
`worktree_content_classification`) with a structural resolution -- e.g.
scan the worktree's own `main..HEAD` history for a `chore(tickets):
record <id> start transition` commit per candidate in-progress ticket
id, the same signal T-2747's `_worktree_started_ticket` now uses for the
leases section -- rather than continuing to assume the `t-<id>` naming
convention holds.