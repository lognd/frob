---
id: T-2738
title: frob ticket close does not promote pending drafts, so a closed ticket's follow-ups
  are silently lost
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- tests/unit/test_close_promote_drafts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: close must promote pending T-draft-* follow-ups the way land does
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_close_promote_drafts.py
  reason: close must promote pending T-draft-* follow-ups the way land does
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_with_no_drafts_is_unchanged
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b864a1074d3e74064cd98a0e3322b27064cedbf9
---
## Measured, 2026-08-20

`frob ticket land` promotes a ticket's `T-draft-*` follow-ups to real
ids as part of landing. `frob ticket close` does NOT. So a ticket closed
rather than landed leaves every draft it filed stranded on a branch,
never promoted, never on main, and invisible to the queue.

Caught live: T-2718 could not land (its own `land` retries kept hitting
BUG002 confirmatory-only) so it was closed directly with
`frob ticket close --skip-mutation-evidence`. Its follow-up draft
`T-draft-cf0b0af7` -- documenting a real defect reproduced live TWICE
during that very series -- existed only on the now-detached `t-2711`
branch at `ce1f406d3`. It was recovered by hand and refiled as T-2737.

Nothing surfaced the loss. The close reported success. The draft simply
was not there afterwards, and only an agent re-reading its own series
notes noticed.

## Why closing instead of landing is a NORMAL path, not an error

This is not an exotic case. A ticket legitimately closes rather than
lands when its content already reached main as a passenger of a sibling's
`--allow-cross-ticket` carry -- which happened repeatedly today (T-2141,
T-2303, T-2718). In each of those the work shipped and only the ledger
state needed settling. So the close path is exercised often, and every
draft filed by such a ticket is currently lost.

## Blast radius

The lost artifact is a FOLLOW-UP TICKET -- by construction, a record of
work someone deliberately chose not to do inline. That is precisely the
class this repo's whole discipline exists to prevent losing: "if scope is
cut, record it explicitly rather than deleting it". A silently dropped
follow-up is indistinguishable from scope that was never cut at all.

## Required

`frob ticket close` must promote pending drafts the same way `land` does,
or must REFUSE, loudly, when the ticket being closed has unpromoted
drafts -- naming them, so the operator can promote them explicitly.
Silently succeeding while discarding them is the failure mode.

## Positive controls, both directions

- close a ticket that filed a draft: the draft is promoted to a real id
  and present on main afterwards (or the close refuses and names it)
- close a ticket with NO drafts: unchanged, no new refusal, no noise
- land a ticket that filed a draft: still promotes exactly as today, no
  regression on the path that already works

## Related

Same family as the unlanded-work leak generally: content that is complete
but lives only on a disposable branch is invisible and gets swept. Two
other instances today -- a critical ticket that existed only on a dead
agent's branch (rescued by hand, became T-2711), and the waive-audit
watermark destroyed with its worktree (T-2721). The common shape is state
written where it will not survive, with no signal that it is about to be
lost.