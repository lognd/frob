---
id: T-3113
title: 'frob ticket block is add-only: a mistaken blocked_by edge cannot be removed
  without hand-editing the ledger'
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/ticket_runner/_lifecycle.py
- tests/test_ticket_lifecycle.py
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'T-3113''s own ask (--reason TEXT mandatory + recorded on unblock, matching
    reopen''s shape) is implemented in _unblock''s runner body, not the CLI parser
    alone; _closeout.py can only add the --reason flag, the actual recording write
    lives in _lifecycle.py::_unblock. T-2681 (landed 2026-08-19) already added unblock
    itself with refuse-loudly-on-missing-edge semantics -- confirmed via git log/xref
    before widening -- so the remaining real gap is narrower than the ticket text
    describes: reason-recording only.'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_ticket_lifecycle.py
  reason: Existing _unblock tests construct AppConfig(ticket_command='unblock', ...)
    without --reason; T-3113 makes --reason mandatory, so every existing call site
    in this file needs updating plus new must-fire/must-stay-quiet fixtures for the
    reason requirement and the Unblock log line.
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: AFFECT001 doc-drift fix for _unblock's changed behavior (T-3113 --reason
    requirement) needed to touch this file.
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: Record the measured dead end, why blocked_by is load-bearing, and the T-3087
    reopen verb as the shape to copy
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 2744
- mode: append
  reason: record the manual pre-fix/post-fix verification for BUG002, since --designate-repro
    cannot succeed against a squashed test+fix commit (T-2025)
  actor: logan
  at: '2026-08-27'
  old_length: 2743
  new_length: 3653
- mode: append
  reason: prior waiver line broke on backslash-continuation across newlines; restate
    as one physical line matching the accepted directive shape
  actor: logan
  at: '2026-08-27'
  old_length: 3652
  new_length: 4547
evidence:
- tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_removes_edge
- tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_when_not_present
- tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_refuses_invalid_ref
- tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_requires_reason
- tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_records_reason_in_unblock_log
- tests/test_ticket_lifecycle.py::TestUnblock::test_unblock_leaves_other_blockers_intact
- tests/test_ticket_lifecycle.py::TestBlockThenUnblockRoundTrip::test_block_then_unblock_round_trips
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. `frob ticket block <id> --by <other>` adds a blocked_by
edge and there is NO INVERSE VERB. An agent blocked T-3101 on T-3089, then
determined the want was satisfiable immediately, and could not undo the edge
without hand-editing the ledger -- which is forbidden and has previously taken
every gate down (a space-hash in prose broke tickets.md YAML). It worked around
the dead end by filing a separate ticket instead, which is a reasonable
recovery but leaves a wrong edge in the graph permanently.

WHY THIS IS MORE THAN AN ERGONOMIC GAP. `blocked_by` is load-bearing: it drives
`frob ticket doable`, the dispatch closure, epic rollups, and now T-3087's
close-time guard, which REFUSES a close while a blocker is non-terminal. So a
mistaken block is not cosmetic -- it can make a ticket undispatchable and
unclosable, with no supported way back. The ledger's mutation surface is
otherwise carefully reversible (`fail` requeues, `reopen` was added today for
exactly this reason on the done edge), which makes this one an outlier rather
than a deliberate design.

Note the precedent set today by T-3087: `frob ticket reopen` was added for the
falsely-closed case, deliberately NOT as a general `DONE -> QUEUED` transition
edge, but as an explicit, reason-carrying, audited verb that leaves the generic
`transition()` refusal intact for every other caller. THAT IS THE SHAPE TO COPY
here -- not a general-purpose mutable `blocked_by` field.

WHAT IS WANTED
- `frob ticket unblock <id> --by <other> --reason TEXT`, reason mandatory,
  recorded in the ticket the same way a block is.
- It must refuse to remove an edge that does not exist, rather than silently
  succeeding -- a no-op that reports success is how a caller comes to believe
  a graph edit happened when it did not.
- Consider whether removing the LAST blocker should be distinguishable in the
  record from a ticket that never had one; the doable closure treats them
  identically but a reader should be able to tell them apart.

ALSO WORTH CHECKING while in this code: audit the rest of the ticket verb
surface for other add-only mutations with no inverse. `block` was not noticed
until an agent needed the inverse under time pressure; there may be siblings.
Report what you find even if you change nothing.

ACCEPTANCE
- `unblock` removes exactly the named edge, requires a reason, and records it.
  Must-fire fixture.
- Unblocking an edge that is not present refuses loudly. Must-fire fixture.
- Other blocked_by edges on the same ticket are untouched. Must-stay-quiet
  fixture.
- The T-3087 close guard and `frob ticket doable` both observe the removal
  immediately; state which invariants you checked.
- The add-only audit of the verb surface is reported.

## BUG002 waiver

frob:waive BUG002 reason="Test-first split into a separate pre-fix commit \
was not performed before this ticket's evidence-binding commit (rapid \
profile, single squashed feat commit). Manually verified the repro \
property instead: checked out src/frob/app/ticket_runner/_lifecycle.py \
at the pre-fix commit (cf3d8913a) with the new test file in place -- \
test_unblock_requires_reason fails with 'DID NOT RAISE SystemExit' \
against the unfixed _unblock (no --reason validation existed), and \
passes against the fixed code. Restored the fixed file immediately \
after (git reset + verified git diff empty). This is the T-2025 \
documented limitation: a newly-added ticket's own history never \
contains the test without its fix already applied once committed \
together, so --designate-repro structurally cannot pass here even \
though the defect and its reproduction are both real."

## BUG002 waiver (corrected)

frob:waive BUG002 reason="Test-first split into a separate pre-fix commit was not performed before this ticket's evidence-binding commit (rapid profile, single squashed feat commit). Manually verified the repro property instead: checked out src/frob/app/ticket_runner/_lifecycle.py at the pre-fix commit (cf3d8913a) with the new test file in place -- test_unblock_requires_reason fails with DID NOT RAISE SystemExit against the unfixed _unblock (no --reason validation existed), and passes against the fixed code. Restored the fixed file immediately after (git reset, verified git diff empty). This is the T-2025 documented limitation: a newly-added ticket's own history never contains the test without its fix already applied once committed together, so --designate-repro structurally cannot pass here even though the defect and its reproduction are both real."