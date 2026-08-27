---
id: T-3087
title: A ticket can reach done with an unsatisfied blocked_by, and a falsely-closed
  ticket cannot be reopened
state: in-progress
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
- src/frob/tickets/_setters.py
- src/frob/tickets/_reporting.py
- src/frob/tickets/_models.py
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_closeout.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: blocked_by close-time refusal lives in _close_cmd (pre-transition guard,
    _evidence.py is leased by T-3038); reopen verb needs a new reason-carrying setter
    (_reporting.py, mirroring drop_ticket), a new TicketError/TicketState transition
    edge (_models.py/__init__.py), and CLI wiring
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/tickets/_models.py
  reason: blocked_by close-time refusal lives in _close_cmd (pre-transition guard,
    _evidence.py is leased by T-3038); reopen verb needs a new reason-carrying setter
    (_reporting.py, mirroring drop_ticket), a new TicketError/TicketState transition
    edge (_models.py/__init__.py), and CLI wiring
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: blocked_by close-time refusal lives in _close_cmd (pre-transition guard,
    _evidence.py is leased by T-3038); reopen verb needs a new reason-carrying setter
    (_reporting.py, mirroring drop_ticket), a new TicketError/TicketState transition
    edge (_models.py/__init__.py), and CLI wiring
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: blocked_by close-time refusal lives in _close_cmd (pre-transition guard,
    _evidence.py is leased by T-3038); reopen verb needs a new reason-carrying setter
    (_reporting.py, mirroring drop_ticket), a new TicketError/TicketState transition
    edge (_models.py/__init__.py), and CLI wiring
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: blocked_by close-time refusal lives in _close_cmd (pre-transition guard,
    _evidence.py is leased by T-3038); reopen verb needs a new reason-carrying setter
    (_reporting.py, mirroring drop_ticket), a new TicketError/TicketState transition
    edge (_models.py/__init__.py), and CLI wiring
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: blocked_by close-time refusal lives in _close_cmd (pre-transition guard,
    _evidence.py is leased by T-3038); reopen verb needs a new reason-carrying setter
    (_reporting.py, mirroring drop_ticket), a new TicketError/TicketState transition
    edge (_models.py/__init__.py), and CLI wiring
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: Record the measured close-time gap, the missing reopen path, and the constraint
    that terminal-state semantics must not be weakened
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3990
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. T-3064 is recorded `[done]` while still carrying
`blocked_by=['T-3066']`, and its own done-report opens:

    "T-3064 is BLOCKED, not implemented."
    "No code change to verify with tests -- nothing outside `tickets/` was
     touched."

Its land commit `9d78e63b5` contains only CHANGELOG.md, changelog.d/,
rapid-debt.jsonl and files under tickets/ -- zero source changes. The 182-node
import SCC it claimed to break is untouched. The work has been refiled as
T-3086.

THE AGENT BEHAVED CORRECTLY. It ran the real refactor verb, hit T-3066's false
refusal, refused to hand-edit imports as a workaround (a standing directive),
traced the root cause, and filed T-3066. There is no agent error here. The
defect is entirely in the ledger: NOTHING REFUSED THE CLOSE.

WHY THIS IS SERIOUS RATHER THAN COSMETIC. A ticket that reads `done` is the
signal the whole queue is built on -- `doable`, epic rollups, the rot alarm and
`fleet_status`'s NEEDS CLOSE list all trust it. A false `done` does not merely
lose one ticket's work; it silently removes that work from the backlog, which
is the same failure class as T-3050 (a land writing state=done with zero code
on main, fixed today) approached from the ledger side rather than the land
side. Two independent paths to the same wrong state in one day is a pattern,
not a coincidence.

TWO SEPARATE DEFECTS, BOTH IN SCOPE:

(1) NO CLOSE-TIME BLOCKED_BY CHECK. Measured: `blocked_by` appears exactly
    once each in `src/frob/tickets/_setters.py` and
    `src/frob/tickets/_store.py`, and neither occurrence is anywhere near a
    close/done/refuse path. `src/frob/gates/` references `blocked_by` only in
    `_milestone.py` and `_waive.py`. So a ticket may transition to DONE with an
    unsatisfied blocker still attached and nothing objects.
    A close with an OPEN blocker should refuse. A close whose blocker is itself
    terminal is fine -- the check is on the blocker's state, not its presence.

(2) NO WAY TO REOPEN A FALSELY-CLOSED TICKET. `frob ticket requeue` refuses:
    "T-3064 is done, not in-progress -- only an in-progress ticket can be
    requeued", and the verb list has no `reopen`. So the only recovery is to
    refile the work under a new id, which is what T-3086 had to do. That loses
    the original ticket's history and silently inflates the done count. Closing
    is currently a one-way door even when the close was wrong.

DO NOT WEAKEN THE TERMINAL-STATE GUARANTEE TO FIX (2). Terminal states are
load-bearing: archive, milestone cuts and the doable closure all rely on done
meaning done. The right shape is an explicit, reason-carrying, audited
transition -- the same posture `fail` already has (it requeues WITH the dead
end recorded) -- not a general-purpose mutable state field.

ALSO CONSIDER, as the cheap high-value check: a done-report that literally says
the work was not implemented, on a land whose diff touches nothing outside
`tickets/`, is mechanically detectable. A FEATURE- or BUG-kind ticket closing
with an empty code diff is at minimum a WARN. Be careful with the exception
list -- docs, epics and pure decision records legitimately close without code,
and `no_scope_declared` already marks several of those.

ACCEPTANCE
- Closing a ticket whose `blocked_by` names a NON-TERMINAL ticket refuses.
  Must-fire fixture.
- Closing a ticket whose blockers are all terminal still succeeds.
  Must-stay-quiet fixture -- do not solve this by refusing every blocked_by.
- A falsely-closed ticket can be reopened through an explicit, reason-carrying
  verb, and the transition is recorded. Terminal-state semantics for archive,
  milestones and doable are unchanged; state which invariants you checked.
- T-3064 specifically is either reopened via the new path or explicitly left
  closed with a note pointing at T-3086. Say which and why.
- If you implement the empty-code-diff WARN, it must not fire on docs-kind,
  epic-tier, or `no_scope_declared` tickets. Fixture per exemption.
