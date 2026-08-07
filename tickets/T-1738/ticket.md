---
id: T-1738
title: 'frob ticket wave: partition the doable set into N mutually scope-disjoint
  groups for parallel dispatch'
state: queued
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_query.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`frob ticket doable` answers "what can ONE agent safely start right now",
filtering candidates whose scope collides with an in-progress lease
(T-0453). That is the sequential question, and it is answered well.

Nobody answers the PARALLEL question: "partition the doable set into N
groups whose scopes are mutually disjoint, so N agents can run at once
without colliding." A coordinator dispatching a wave has to do that by
hand, and the only cheap hand-proxy is thematic grouping -- "these are
all docs tickets", "these are all gate false positives" -- which is not
the same property at all.

Observed cost, 2026-08-06, in one session:

- A coordinator grouped three waves by theme instead of by scope. Two
  tickets in one wave (T-1699, T-1705) turned out to be scope-blocked by
  leases held by agents dispatched earlier in the SAME wave planning
  pass. `doable --show-blocked` knew; nothing had asked it.
- T-1679 and T-1637 were thematically unrelated and scope-adjacent:
  T-1679 renamed tests that T-1637 (already closed) had bound its
  evidence to. The rename landed green under `--ticket` scoping and broke
  a closed ticket's evidence on main. Theme said "safe"; scope said
  otherwise.

Build the parallel answer:

    frob ticket wave --agents N [--json]

Returns N groups drawn from the doable set such that no two groups share
a scope glob, each group ordered for sequential execution within itself,
plus an explicit REMAINDER list of doable tickets that could not be
placed disjointly -- and WHY (naming the ticket and the shared glob they
collide on). The remainder is the important half: silently dropping
unplaceable tickets would make a wave look complete when it is not.

Requirements:

- Collision must be computed on RESOLVED scope, the same substrate
  `doable`'s T-0453 filter already uses. Do not re-implement glob
  matching -- extract and share whatever `doable` uses, or this grows a
  second answer to the same question that can disagree with the first.
- Groups must also respect blocked_by ordering: a group is a sequence an
  agent works in order, so a ticket must never precede its blocker.
- Deterministic for a given queue state, so two coordinators planning the
  same wave get the same plan.
- N is a hint, not a guarantee: returning fewer, larger groups is correct
  when the queue does not partition further. Say so in the output rather
  than padding groups with colliding work.
- Prefer packing by priority: a group containing a critical ticket should
  not be the one left unplaceable.

A LIKELY FINDING, WORTH REPORTING RATHER THAN DESIGNING AROUND: this
repo's queue may barely partition at all, because `docs/modules/
tickets.md` appears in a large fraction of every ticket's scope and
therefore collides with almost everything. `--show-blocked` currently
shows a dozen tickets all held on that single path, and two in-progress
tickets mutually blocking each other on it. If the wave command finds it
cannot produce more than one or two disjoint groups, that is a real
measurement of a real bottleneck and should be REPORTED as the result,
not worked around by loosening the collision rule. File what you find;
the remedy (splitting that doc, or making doc scope-leases granular per
heading anchor rather than per file) is a separate ticket and a bigger
decision than this one.

Related: T-1344 (the land path is the throughput bottleneck) is the
adjacent framing; this ticket is about the DISPATCH side of the same
throughput problem.