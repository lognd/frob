---
id: T-1986
title: 'TICK009 only warns, so a ticket can start with an umbrella scope and lease
  most of the repo: 2 caught by hand today, queue will not partition'
state: in-progress
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). TICK009 flags an over-broad ticket
scope as a WARNING. Nothing refuses it, so a ticket can be started with
an umbrella glob and take a cross-worktree lease over most of the repo,
serializing every other agent for the duration.

MEASURED -- two tickets caught by hand this session, both by a
coordinator who happened to look, neither by the tooling:
- T-1664 declared `src/frob/gates/**` (TICK009: "matches 74 files (> 25)"),
  plus `docs/**` and `tests/**`. Caught minutes before `ticket start`;
  narrowed to 4 concrete files and landed without blocking anything.
- T-1638 declared `src/frob/app/ticket_runner/**`, `src/frob/tickets/**`,
  `tests/**` and `docs/**` -- four umbrellas. Found only because an
  unrelated probe printed the scope. Narrowed to 2 files.
- T-1665 still carries `tests/**` and is the one outstanding nudge.

THE COST IS THE WHOLE QUEUE, NOT ONE TICKET. `frob ticket wave --agents 4`
-- the tool that exists to partition doable work into scope-disjoint
groups -- returned ONE group of 28 tickets, because scope unions overlap
so heavily the queue does not partition. Parallel dispatch here is capped
by scope breadth, not by agent count or land contention. Separately,
T-1638 and T-1748 were blocked for a full cycle by a lease on
`src/frob/tickets/_land.py`, and an agent spent its entire dispatch
discovering that collision instead of working.

THE WARNING IS ALREADY WRITTEN AND ALREADY IGNORED. TICK009 has been
printing `N scope-breadth nudge(s) outstanding` on every `frob ticket
doable` run all session. It was read repeatedly and acted on only when a
coordinator manually intervened. Per the standing audit rule: a rule that
is already stated and still not followed is not fixed by stating it
louder.

WHY `ticket start` IS THE RIGHT MOMENT: at `ticket new` the author often
genuinely does not know which files the work touches -- an over-broad
scope is an honest placeholder. By `ticket start` the investigation has
happened, and it is the exact moment the LEASE is taken, so it is the
moment the breadth actually costs other agents something. Refusing there
forces narrowing when the information exists and the cost is real.

DO NOT FIX IT THIS WAY:
- Do NOT make TICK009 a hard error at `frob check`. That reds the floor
  (currently ZERO) for a condition that is legitimate on a
  not-yet-started ticket, and it punishes the author at the wrong moment.
- Do NOT auto-narrow a scope by guessing which files the work will touch.
  Guessing wrong produces a SCOPE001 refusal mid-implementation, which is
  worse than the umbrella.
- Do NOT ban `**` globs outright. Some tickets legitimately span a
  package, and an epic's tracking scope is a real case. The refusal must
  be overridable with a stated reason, so a genuine wide scope is an
  explicit, recorded decision rather than an accident.

FIX DIRECTION, preferred order:
(a) `frob ticket start` REFUSES when the ticket's scope trips TICK009,
    naming the offending globs and the file count, and telling the agent
    to `scope --remove`/`--add` first. Overridable with an explicit
    reason that is recorded on the ticket.
(b) Failing that, surface the breadth in `frob ticket wave`'s output so a
    dispatcher sees which ticket is preventing partitioning.

ACCEPTANCE: first test must FAIL before the fix -- create a ticket scoped
`src/frob/gates/**`, call `ticket start`, and assert it refuses naming
the glob and its file count. Then assert a narrowly-scoped ticket starts
unchanged, and that the override path records its reason on the ticket.
Finally, re-run `frob ticket wave --agents 4` on this repo and report
whether the queue partitions into more than one group once the
outstanding umbrellas are narrowed.
