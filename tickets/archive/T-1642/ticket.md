---
id: T-1642
title: Burn down gate:TICK warnings (TICK003/004/007/009/011)
state: done
kind: docs
origin: agent
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets-archive.md
  reason: TICK011's Done-report scan reads load_queue() which merges active+archive;
    the two live TICK011 findings (T-1262, T-1531) both need their citation fix applied
    wherever their Done report actually lives, and T-1262's has since moved to tickets-archive.md
  actor: logan
  at: '2026-08-06'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:bash -c "grep -q T-1544 tickets-archive.md && grep -q T-1549 tickets-archive.md"
  exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
Burn down gate:TICK warnings (T-1444 dispatch brief: TICK009 x184 mentions,
TICK004 x22, TICK007 x12, TICK011 x4, TICK003 x2 -- unwaived total 112;
measured live at dispatch time: TICK009=96, TICK004=11, TICK007=3-6
(fluctuates with wall-clock age), TICK011=2, TICK003=1).

Classification, per rule -- and the headline finding: every gate:TICK rule
is ledger/process HYGIENE state, not source-code debt. There is no
function to patch; the "fix" is either a mechanical maintenance command
or a per-ticket judgment call about a ticket this agent does not own.

- TICK003 (un-archived closed tickets, threshold 20): (a) real, mechanical.
  Fixed by running `frob ticket archive` in this session (see Done
  report/evidence).
- TICK004 (rotting queued/high-priority tickets past their age threshold,
  11 live): (c) not fixable by this dispatch -- each finding names a
  DIFFERENT ticket this agent does not own and has no context to
  reprioritize or drop responsibly. `frob ticket priority <id> <level>`
  or `frob ticket drop <id> <reason>` are the real remedies, one
  judgment call per ticket, by whoever owns that ticket's context.
- TICK007 (dispatchable-and-unleased-too-long, fluctuates 3-6 live): same
  reasoning as TICK004 -- (c), owner judgment per ticket, not a code fix.
- TICK009 (over-broad ticket scope glob, 96 live, by far the largest
  count): (c) for the bulk, with one real rule-level observation --
  T-1484 already built the correct discretion channel for this
  (`frob ticket scope-ack`, an intentional-broad-scope acknowledgment)
  but adoption is the gap, not the mechanism. Narrowing 96 tickets'
  scope globs by hand, sight-unseen, from outside this dispatch's own
  context is exactly the kind of blind edit the playbook warns against
  (risks breaking another agent's in-flight declared scope) -- the
  responsible per-ticket action is each ticket's own owner running
  `frob ticket scope <id> --add <files> --reason "..."` (narrow) or
  `frob ticket scope-ack <id> --reason "..."` (genuinely-broad epic), not
  a blind bulk edit from this ticket.
- TICK011 (Done report discloses a cut with no follow-up ticket cited,
  2 live at dispatch time -- T-1262, T-1531): (a) real, and the one part
  of this family actually actionable from inside this ticket, since it is
  about REVIEWING TWO SPECIFIC PAST DONE REPORTS, not touching other
  tickets' live state. Investigated and resolved by filing the two named
  follow-ups directly (see Done report for the real ids).

Recommendation for the honest remainder (TICK004/007/009, ~110 findings
across other tickets' own scope): this is a standing backlog-hygiene
sweep, not a burn-down a single dispatched ticket can close -- it needs
either (1) a coordinator-level triage pass across the named tickets
(reprioritize/drop/scope-ack/narrow, one decision per ticket, by someone
with context on each), or (2) `frob ticket doable`/`frob check --only
tickets` folded into a recurring session-start ritual so it never
re-accumulates this large again. Filing a single mechanical ticket to
"fix" 110 other tickets' scope/priority fields would not be a fix -- it
would be exactly the same blind mass edit this dispatch declined to do,
just moved one layer of indirection away.