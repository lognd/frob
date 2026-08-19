---
id: T-2617
title: worktree classifier reports 18 STRANDED where the verified answer is stale-behind-main,
  reproducing the exact test T-2599 specified against
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- scripts/fleet_status.py
- docs/guides/coordinator-scripts.md#worktree_content_classification
- docs/guides/coordinator-scripts.md#_parse_ticket_frontmatter_text
- docs/guides/coordinator-scripts.md#ticket_frontmatter_on_main
- docs/guides/coordinator-scripts.md
- tests/unit/test_coordinator_scripts.py
- tickets/T-2625/ticket.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: T-2617 fix changes worktree_content_classification's documented algorithm
    (land_commit ancestry + deletion-ratio short-circuits); docs move in the same
    change per playbook sec 4
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: T-2617 fix changes worktree_content_classification's documented algorithm
    (land_commit ancestry + deletion-ratio short-circuits); docs move in the same
    change per playbook sec 4
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: docs/guides/coordinator-scripts.md
  reason: narrow to the exact anchors changed; whole-file scope pulled in 200+ unrelated
    pre-existing SCOPE002 findings
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/coordinator-scripts.md#worktree_content_classification
  reason: narrow to the exact anchors changed; whole-file scope pulled in 200+ unrelated
    pre-existing SCOPE002 findings
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/coordinator-scripts.md#_parse_ticket_frontmatter_text
  reason: narrow to the exact anchors changed; whole-file scope pulled in 200+ unrelated
    pre-existing SCOPE002 findings
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/coordinator-scripts.md#ticket_frontmatter_on_main
  reason: narrow to the exact anchors changed; whole-file scope pulled in 200+ unrelated
    pre-existing SCOPE002 findings
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'SCOPE001: docs file edited (algorithm doc for worktree_content_classification),
    test file edited (new coverage), draft ticket file created for the filed follow-up'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: 'SCOPE001: docs file edited (algorithm doc for worktree_content_classification),
    test file edited (new coverage), draft ticket file created for the filed follow-up'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2625/ticket.md
  reason: 'SCOPE001: docs file edited (algorithm doc for worktree_content_classification),
    test file edited (new coverage), draft ticket file created for the filed follow-up'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_superseded_symbol_with_landed_terminal_ticket_is_stale
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_genuinely_new_symbol_absent_from_main_is_stranded
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_far_behind_main_with_no_ticket_is_stale
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_terminal_ticket_land_commit_is_ancestor_of_main
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_survives_terminal_ticket_with_unlanded_land_commit
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stale_when_deletion_dominant
- tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification::test_stranded_survives_a_small_mostly_additive_diff
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassificationLiveGit::test_superseded_symbol_with_landed_terminal_ticket_is_stale
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e70e5961d228fc955e123993cd25af17b71b1ca6
---
## Measured against real data, immediately after T-2599 landed

    scripts/fleet_status.py  ->  WORKTREES (STRANDED: 18)

Spot-checking the flagged set shows the classification is wrong for at
least the cases verified, and wrong in the direction T-2599's own body
warned about.

**t-2576, flagged STRANDED.** T-2576 landed successfully earlier today
(`LAND-PROOF verified=True`). Its diff versus main is `+17 / -985`, and
inspecting the `+` side:

    +    _write_baseline(root, fresh, actual_head)
    +    if not _baseline_write_survived(root, actual_head):
    +def _other_open_tickets(queue: TicketQueue, ticket: Ticket) -> ...

Every one of those is an OLDER version of code main has since replaced --
`_write_baseline` was superseded by T-2595's `_write_baseline_cas`,
`_baseline_write_survived` by the same land, `_other_open_tickets` by M4
work. Nothing exists only in the worktree. It is BEHIND main, not ahead.

**t-2593, flagged STRANDED.** Also landed (as a drop) today. `+11 / -558`,
same shape.

**gate-internals, flagged STRANDED.** `+12618 / -110259` -- a worktree
~13400 minutes idle that main has moved far past.

**t-1599, flagged ACTIVE.** T-1599 is a QUEUED story with no live work.
ACTIVE is the safe direction so this is lower priority, but the ticket-state
input appears not to be consulted.

## This is the failure the ticket explicitly specified against

T-2599's body documented three detection tests that all give wrong answers,
and the shipped behavior reproduces the third one verbatim:

> reading the insertion count alone -- still wrong without checking
> DIRECTION. `t-2588` showed "1 insertion not on main"; inspecting it, the
> line was an OLD one-line docstring that main had deliberately REPLACED.

Its mandatory positive control was equally explicit:

> a worktree merely behind main (large deletion-side diff) is STALE, not
> STRANDED -- test 2's failure

That control does not hold on real data. The implementation's own tests
pass, so they are presumably synthetic fixtures that never construct the
superseded-content case -- which is the only case that distinguishes a
correct classifier from a naive one.

## Why it matters

18 false STRANDED marks make the signal useless in the harmful direction:
an operator either preserves every worktree forever or learns to ignore the
flag, and ignoring it is exactly how genuinely stranded work gets swept.
A classifier that says STRANDED for everything is not safer than none -- it
is a louder version of no information.

## Fix

Compare the `+` side against main's CURRENT content, not merely against the
merge-base or the commit list. Content is stranded only if it exists in the
worktree and has NO counterpart on main. A superseded line -- same symbol,
different body, main's version newer -- is STALE.

Consult the ticket's state as well: a worktree whose ticket is terminal AND
whose land commit is an ancestor of main cannot be stranded regardless of
diff shape.

## Positive controls -- these must run against REAL worktrees, not only fixtures

The existing unit tests pass while the behavior is wrong, so add at least
one check that exercises the live repo:

- a worktree for a ticket that LANDED (t-2576, t-2593) is STALE, never
  STRANDED
- a long-idle worktree far behind main (gate-internals) is STALE
- a worktree containing a symbol that does NOT exist on main at all is
  STRANDED -- construct this deliberately; without it the fix is
  indistinguishable from classifying everything STALE
- report the STRANDED count against a known denominator and state it