---
id: T-1347
title: frob ticket brief emits concurrent sibling leases so dispatch is one line
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/tickets/_brief.py
- docs/modules/tickets.md
- src/frob/tickets/_reporting.py
- tests/test_tickets_brief.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: brief_ticket wiring + its tests live in these files, needed to thread concurrent
    in-progress tickets through
  actor: logan
  at: '2026-07-31'
- op: add
  glob: tests/test_tickets_brief.py
  reason: brief_ticket wiring + its tests live in these files, needed to thread concurrent
    in-progress tickets through
  actor: logan
  at: '2026-07-31'
evidence:
- tests/test_tickets_brief.py::TestConcurrentLeases::test_lists_others
- tests/test_tickets_brief.py::TestBriefTicket::test_concurrent_leases
designated_repro_test: null
acceptance:
- text: given other tickets in progress, when frob ticket brief runs, then it lists
    their ids, titles, and scope globs under a do-not-touch heading
  evidence:
  - tests/test_tickets_brief.py::TestConcurrentLeases::test_lists_others
  - tests/test_tickets_brief.py::TestBriefTicket::test_concurrent_leases
threat: null
component: tickets
---
Leaf of T-1344. Trivial, do this first -- it is the cheapest item in the epic.

"frob ticket brief" already emits a complete mission briefing: description+plan, scope+leases, playbook hard rules, targeted verify commands, gate baseline, REL/land rules. On 2026-07-31 the coordinator was nonetheless hand-writing 40-line dispatch prompts that duplicated it, because brief was missing exactly ONE thing: the scopes of the OTHER tickets currently in flight.

With 7 concurrent agents, the do-not-touch list is the single most important thing a dispatched agent needs and the only thing the coordinator must still supply by hand.

PROPOSAL: brief emits a "Concurrent leases (do NOT touch)" section listing every OTHER in-progress ticket's id, title, and scope globs, resolved live at brief time. Then a dispatch prompt collapses to: "work T-XXXX; run frob ticket brief T-XXXX and follow it; playbook governs."

Also worth folding in, from the same session's observations:
- Note the interrupted-land hazard: commit new tests BEFORE running land, because a killed land can garble a file and the "git checkout --" recovery then eats uncommitted work (T-1338).
- Note that transient DirtyMain refusals under concurrency are EXPECTED and the correct response is wait-and-retry, never touching main.