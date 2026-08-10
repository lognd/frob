---
id: T-1960
title: 'WIRE001 follow-ups inherit no priority, so the half that makes a fix real
  starves: 7 open, all medium, 3 from high parents'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). WIRE002 guarantees that a
`frob:waive WIRE001` NAMES a follow-up ticket. It does not, and cannot,
guarantee that the follow-up is ever LANDED. The result is a legal,
gate-clean way to ship a detector that nothing calls, close the ticket as
`done`, and leave the hole it was filed to close still open.

MEASURED -- 7 open "wire X into Y" tickets, EVERY ONE at priority=medium:
  T-1942  Wire examined-sites as a third WAIVE004 mass-invalidation guard
  T-1956  Wire find_unregistered_rule_ids into the T-0756 acceptance preflight
  T-1957  Wire DUP001 region_kernel as regression corpus for type-name dup
  T-1584  Wire frob profile CLI to frob.tickets._profile
  T-1777  Wire force_release_lease into a CLI verb
  T-1820  frob quality bind's argparse dests are permanently unwired
  T-1691  Bisect the unattributable residue of a red batch

THE PRIORITY INVERSION IS THE DEFECT. The first three were all created in
a single two-hour window, each as the completing half of a HIGH-priority
parent:
  T-1921 (WAIVE004 escape substrate) -> T-1942  high -> medium
  T-1937 (rule registry soundness)   -> T-1956  high -> medium
  T-1938 (DUP001 type-name blind spot) -> T-1957 high -> medium

So the half that makes the fix REAL is systematically filed at lower
priority than the half that merely builds the machinery -- and then
starves behind newer high-priority work. T-1937's own done-report is
explicit: `find_unregistered_rule_ids` "has no production caller yet
(WIRE001) -- waived with follow_up". T-1937 is `done`. The soundness hole
it was filed to close is still open.

This is the catalogued-is-not-enforced failure in its purest form: a
registry/detector that no code path reads is documentation wearing a
gate's clothing. A completion claim needs a passing GATE, not a named
follow-up ticket.

DO NOT FIX IT THIS WAY:
- Do NOT ban shipping a detector unwired. That is sometimes exactly
  right: T-1921 was DELIBERATELY left unwired on coordinator instruction,
  because shipping the substrate and its consumer in one change is how
  the 55-live-waiver deletion happened. Separating build from wire is a
  safety practice worth preserving.
- Do NOT weaken or auto-expire WIRE001 waivers. An expiring waiver just
  turns into noise or a forced bad wire-up under time pressure.
The defect is not that unwired code ships; it is that nothing carries the
PRESSURE forward once it does.

FIX DIRECTION, preferred order:
(a) At the moment the follow-up is created, have it INHERIT the priority
    of the ticket whose waiver named it. A high-priority hole does not
    become a medium-priority hole because it was split in two.
(b) Failing that, surface open WIRE001 follow-ups where the operator
    already looks -- `frob ticket doable` already prints stale-lease and
    unlanded-work lines; an "N detectors shipped unwired, oldest Xh" line
    belongs beside them.
(c) A ratchet: the count of open WIRE001 follow-ups may not increase.

ACCEPTANCE: first test must FAIL before the fix -- create a high-priority
ticket whose close waives WIRE001 with a follow_up, and assert the
created follow-up is ALSO high. Then assert a medium parent yields a
medium follow-up (no blanket escalation). Then report the current 7 open
follow-ups with corrected priorities.
