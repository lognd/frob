---
id: T-1853
title: An anchor ticket cited by a permanent waiver can never land ANY ledger record,
  not just close
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`_check_live_tracker_citations` (`src/frob/tickets/_land.py`) refuses to
land ANY ticket while code still cites it as a live tracker
(`frob:waive ... follow_up="T-####"`, or a registry `deferred:`/
`tracked_by:` disposition). It fires regardless of whether those
citations were already present, unchanged, at `base_ref`.

That makes a whole class of ticket permanently unlandable: the ANCHOR
ticket, whose entire purpose is to stay open forever so that a
permanent-by-design waiver has a valid `follow_up` target.

OBSERVED on T-1820. Three `frob:waive WIRE001 follow_up="T-1820"`
directives live in `src/frob/_cli_parsers/_quality.py` (lines 92, 101,
108) and were on main before any of this session's work began. Every
`frob ticket land T-1820` therefore refuses:

    land: T-1820 cannot land -- 3 site(s) still cite it as their live
    tracker ... -- file a successor ticket and re-point these rows, or
    re-point them in this same change, then retry

The suggested remedy is wrong for this shape. Re-pointing to a successor
does not resolve anything: the exemption is permanent, so the successor
becomes the identical permanent anchor under a new id, and the old id is
churned for nothing. There is no state in which those citations go away.

WHY ANCHOR TICKETS EXIST. WIRE002 is unwaivable and fires when a
`follow_up` names a ticket that is `done` or `dropped` -- the T-1490/
T-1488 incident orphaned 16 waivers at once that way. Only terminal
states disqualify a target, so an anchor must sit in a non-terminal
state indefinitely. `docs/modules/gates.md` records this as the T-1558
"waiver home" precedent. The design is deliberate and correct.

The conflict is that `land` treats "land this ticket" as "this ticket is
being finalized," which is true for ordinary tickets and false for
anchors. The consequence is not just that an anchor cannot close -- it
cannot land ANY ledger record at all. A `frob ticket fail` attempt log,
a scope change, an evidence binding: all unlandable for the life of the
ticket. That is a silent data-loss path of exactly the shape T-1818 was
filed to close for fail records generally.

REQUIRED:

1. Distinguish "landing a ticket's ledger record" from "finalizing a
   ticket". `_check_live_tracker_citations` should only fire when the
   land would move the ticket to a TERMINAL state (`done`/`dropped`).
   A land that leaves it `queued` or `in-progress` threatens no citation
   and must be allowed.
2. Consider a first-class marker for this class -- an explicit
   `anchor: true` or a dedicated kind -- so the intent is declared
   rather than inferred from "it happens to be cited". Today the only
   signal that a ticket must never close is prose in its body, which
   nothing enforces and which a well-meaning agent will eventually
   close in the name of draining the queue. That nearly happened today.
3. Whatever the fix, the refusal must stop recommending a successor
   re-point for permanent exemptions; that advice actively destroys the
   anchoring it is meant to protect.

Note the near-miss: an agent was instructed (by me) to "actually do
T-1820" once its file lease cleared. Another agent had already
determined there was nothing to do and that closing it would trip
WIRE002 and orphan three waivers. The tool offered no signal either
way -- both the instruction and the refusal pointed at destroying the
anchor.
