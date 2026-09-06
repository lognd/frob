---
id: T-4063
title: 'F-269: stale waivers citing a ticket as their live tracker block that ticket''s
  close, though SELFAUDIT already knows they match nothing'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_waive_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-269, 2026-09-06:

  "T-0014 COULD NOT CLOSE until two SYSWAIVE002 waivers in
   design/logand-app.strata (SYS101:client_storage, SYS101:html_render) THAT
   STILL CITED T-0014 AS THEIR LIVE TRACKER were removed; SELFAUDIT001 SHOWED 0
   MATCHING FINDINGS, i.e. they were long stale. A waiver whose finding no longer
   fires should be reported as stale by `frob check` (SELFAUDIT ALREADY KNOWS)
   and offered for removal at close time, not discovered by the close refusal."

A TICKET WAS BLOCKED BY WAIVERS THAT NAMED IT AS THEIR REASON FOR EXISTING. The
waivers cite T-0014 as their live tracker, so T-0014 must stay open to justify
them; T-0014 cannot close while they cite it. That is circular by construction --
the ticket is held open by artifacts whose only claim on it is that it is open.

THIS IS THE no-exit CLASS, and it is the ELEVENTH instance in this queue. It also
has DIRECT PRIOR ART IN OUR OWN CODE. src/frob/app/ticket_runner/_land_cmd.py
carries this note verbatim on a waiver it wrote for itself:

    "does not expire -- follow_up points at T-3504 (open, unrelated), not the
     ticket landing this change: A WAIVER CITING ITS OWN LANDING TICKET BLOCKS
     ITS CLOSE (T-2280's own LiveTrackerCited lesson)"

So we HIT THIS OURSELVES, learned it, and encoded the workaround as a convention
that authors must remember: point follow_up at some OTHER open ticket. That is
the same failure mode as every other item in this cluster -- a real constraint
enforced only by lore, with no mechanism, and it recurs the moment someone does
the natural thing.

THE STALENESS HALF IS THE ACTIONABLE ASK AND IT IS CHEAP, because the information
already exists. Their key observation: SELFAUDIT001 reported ZERO matching
findings for both waivers. So the system already knew the waivers were dead; it
simply never said so until an unrelated operation refused. Note this repo has
machinery for exactly this -- WAIVE004 handles stale-waiver detection
(src/frob/app/ticket_runner/_waive_audit.py, and its auto-fix has a
degraded-run guard apollo confirmed working today). VERIFY WHY WAIVE004 DID NOT
COVER SYSWAIVE002 before building anything new: if it is a coverage gap in an
existing rule, that is a much smaller fix than a new mechanism, and this repo has
had four "nothing enforces X" claims turn out already-implemented.

TWO DELIVERABLES, and the first is independently useful:
1. REPORT A STALE WAIVER AS STALE, at check time, wherever SELFAUDIT/WAIVE
   already knows its finding no longer fires. A waiver suppressing nothing is
   dead weight that will eventually block something; surfacing it early costs
   nothing.
2. BREAK THE CIRCULARITY AT CLOSE. When close refuses because waivers cite the
   closing ticket, it should say so precisely -- naming the waivers and the fact
   that they name this ticket -- and offer the removal. Today the refusal reports
   the symptom and leaves the user to discover the loop.

DO NOT fix this by letting close ignore waivers that cite it. A waiver citing a
LIVE ticket is a real constraint in the general case; the defect is the
combination of that constraint with a stale waiver and an uninformative refusal,
not the constraint itself.

MUST-FIRE FIXTURE: a waiver whose finding still fires and which cites an open
ticket still blocks that ticket's close.
MUST-STAY-QUIET: a waiver whose finding no longer fires is reported as stale at
check time, before any close is attempted.
THIRD FIXTURE: a close refused by self-citing waivers names them and states the
circularity.

ACCEPTANCE
- Why WAIVE004's stale detection does not cover SYSWAIVE002, answered first.
- Stale waivers surfaced at check time from information already computed.
- The self-citation refusal made self-explaining.
- All three fixtures committed.