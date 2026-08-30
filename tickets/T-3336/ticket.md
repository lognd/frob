---
id: T-3336
title: frob ticket close reports success on a ticket land then refuses as NotCloseable,
  and done-report does not mirror like its sibling verbs
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_done_report.py
- src/frob/tickets/_evidence.py
- tests/test_tickets.py
- tickets/T-3468/**
- frob.lock
- tickets/T-1585/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: T-3336's actual defect 1 code (close's rapid-profile bypass covering the
    missing-evidence/Done-report check that land's own NotCloseable gate never relaxes)
    lives in _evidence.py::_done_transition_structural_guard, not in _done_report.py
    -- the ticket's declared scope names only the hollow-report/stale-claims leaf
    module, which does not contain the divergence being fixed
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_tickets.py
  reason: T-3336 updates the existing rapid-leniency/hollow-report tests in test_tickets.py
    for the new unconditional evidence gate, and files the required defect-2/defect-3
    follow-up ticket whose ticket.md write needs to be in scope
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-3468/**
  reason: T-3336 updates the existing rapid-leniency/hollow-report tests in test_tickets.py
    for the new unconditional evidence gate, and files the required defect-2/defect-3
    follow-up ticket whose ticket.md write needs to be in scope
  actor: logan
  at: '2026-08-30'
- op: add
  glob: frob.lock
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-1585/**
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: frob.lock
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-1585/**
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: frob.lock
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-1585/**
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: frob.lock
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-1585/**
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: frob.lock
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-1585/**
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: frob.lock
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-1585/**
  reason: frob ack writes frob.lock; rebinding T-1585's stale evidence citation (frob
    ticket evidence --replace) writes that archived ticket's file
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'second independent instance with the exact mechanism: land''s NotCloseable
    requires pytest evidence regardless of profile or --no-behavior-change, while
    close''s rapid-profile bypass covers it -- a second divergence point beyond the
    Done-report heading'
  actor: logan
  at: '2026-08-29'
  old_length: 4130
  new_length: 6691
evidence:
- tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_missing_evidence_and_done_report_still_refuses
- tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_non_rapid_missing_evidence_and_done_report_still_refuses
- tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_with_real_evidence_and_done_report_lands_without_extra_steps
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-28 landing T-3277. Two defects in the same seam, both found
because a land refused for a reason its own close had reported success for.

DEFECT 1: CLOSE AND LAND DISAGREE ABOUT WHAT "CLOSED" MEANS.

`frob ticket close` succeeded. Under the rapid profile's relaxed evidence rule
it reported success and moved the ticket to `done`. But it never produced the
one artifact `frob ticket land`'s NotCloseable check actually greps for: a
literal `## Done report` heading.

The subsequent land refused:

    ERROR: land: T-3277 cannot land -- missing evidence or a Done report
    ERROR: ticket land failed: NotCloseable

So a ticket can be `state: done` locally, with a close that reported success,
and still be structurally unlandable. The coordinator hit this independently
before the owning agent did -- I attempted the land, got the same refusal, and
could not tell from the ticket whether the agent had failed to write a report
or the gate was wrong.

CONTRIBUTING CAUSE, worth stating because it is its own trap: the agent wrote
its Done report through a body-append, deliberately AVOIDING the literal
"## Done report" heading, because the append tool refuses text containing that
heading as an ambiguous edit target. So one tool's safety check pushed the
content into a shape a second tool's gate cannot see. Neither tool is wrong on
its own terms.

DEFECT 2: `frob ticket done-report` DOES NOT MIRROR TO THE PRIMARY CHECKOUT.

`body`, `evidence` and `new` all mirror a worktree write back to the primary
checkout. `done-report` does not. The agent had to run it TWICE -- once in the
worktree so the land would see it, once directly against the root so main would
have it -- and that duplication then produced an add/add merge conflict on
`tickets/T-3277/done-report.md` when the two independently-generated copies
met, resolved by hand.

So the workaround for defect 2 manufactures a third problem.

WHY THIS MATTERS BEYOND ONE STUCK LAND. `close` reporting success while leaving
the ticket unlandable is the same shape as this project's dominant defect
class: an operation reports a state it has not actually achieved. It cost two
separate agents multiple attempts on one ticket, and neither could diagnose it
from the ticket's own contents. In a consumer repo, where the operator does not
have frob's source open in another window, this is a dead end.

WHAT TO BUILD:
  1. Make close and land agree. Either close PRODUCES what land requires, or
     close REFUSES with the same message land would give. Do not leave a state
     that one verb calls success and the next calls NotCloseable. State which
     direction you chose and why.
  2. `done-report` must mirror like its siblings, or must say plainly that it
     does not and what to run. Silent asymmetry between sibling verbs is the
     trap here -- the agent reasonably assumed it behaved like `body`.
  3. Resolve the heading collision at the root: one tool refuses text
     containing `## Done report` while another requires exactly that heading.
     Whatever the fix, those two rules must be made aware of each other rather
     than each being locally correct.

DO NOT FIX THIS BY LOOSENING LAND'S NotCloseable CHECK. Requiring a real Done
report before publishing is correct and is the guard that makes done-reports
trustworthy at all. The defect is that close does not produce what land
demands, not that land demands it.

MUST-FIRE FIXTURE: a ticket closed under the rapid profile without a Done
report is refused AT CLOSE TIME, with the same wording land would use.
MUST-STAY-QUIET FIXTURE: a normal close that produces a Done report lands
without extra steps.
THIRD FIXTURE: `done-report` written in a worktree is visible in the primary
checkout without a second manual invocation, and produces no add/add conflict.

ACCEPTANCE
- No state exists where close succeeds and land reports NotCloseable for the
  missing-report reason.
- `done-report`'s mirroring behaviour matches its siblings or is documented at
  the point of use.
- The heading collision between the append guard and the land gate is resolved.
- All three fixtures present.


SECOND INDEPENDENT INSTANCE, WITH THE EXACT MECHANISM. 2026-08-29, Series EJ,
found while landing T-2667.

The original filing described the symptom -- `frob ticket close` reports success
on a ticket that `frob ticket land` then refuses as NotCloseable -- and named a
contributing cause (a body-append that avoided the literal "## Done report"
heading). This is a DIFFERENT path to the same divergence, and it names the
code:

    land's NotCloseable check:
        if not ticket.evidence or not _has_done_report(...)

    It requires a real pytest evidence id REGARDLESS of profile and REGARDLESS
    of --no-behavior-change. Close's rapid-profile debt bypass covers that
    requirement; LAND'S OWN GATE DOES NOT.

So a `kind=bug` ticket closed legitimately under the rapid profile with
`--no-behavior-change` -- a comment-only accounting change with no runtime delta
and therefore no pytest node that can fail-then-pass -- passes close and is
refused by land. The two verbs disagree about what "closeable" means, and the
disagreement is in the evidence requirement, not only in the report heading.

EJ's workaround was to bind an ACCURATE but incidental evidence id
(tests/test_gates.py::TestDebtGate::test_debt002_open_ticket_is_silent -- real
behaviour its directive relies on). That is the honest version of the
workaround, but it is still a workaround: the ticket had no behaviour change to
evidence, and the requirement pushed it toward binding something adjacent.

WHY THIS SHARPENS THE FIX. The original body asked for close and land to agree,
without saying where they diverge. There are now TWO measured divergence points:
  1. The Done-report heading requirement (original instance).
  2. The evidence requirement under rapid profile + --no-behavior-change (this
     instance).
Both are land demanding something close does not produce. A fix that only
reconciles the heading leaves this one open.

THE DESIGN QUESTION TO ANSWER EXPLICITLY: should a no-behaviour-change ticket
be required to cite pytest evidence at all? There is a real argument either way.
Requiring it means every accounting fix binds an incidental test, which dilutes
what evidence means. Not requiring it means land trusts a close-time
declaration, which is the trust boundary land exists to check. State the choice
and the reasoning; do not just make the error go away.

DO NOT fix this by removing land's evidence check. It is the guard that makes
done-reports trustworthy, and this repo has a documented history of tickets
reaching `state: done` with nothing behind them.