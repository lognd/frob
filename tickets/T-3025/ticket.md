---
id: T-3025
title: 'A single trivial unattributed finding disables fleet-wide landing: four occurrences
  today, ~90 minutes lost, no severity proportionality'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
A SINGLE trivial, unattributed finding raises quarantine, and a raised
quarantine turns OFF deferred rapid landing REPO-WIDE, forcing every land to run
fully-synchronous verification. Under a multi-agent fleet that reliably pushes
lands past the 540s shell ceiling, so lands stop completing at all.

FOUR OCCURRENCES IN ONE DAY (2026-08-26), all the same shape -- a trivial,
auto-fixable finding recorded with `commit=None, ticket=None`:

  1. `I001` (import sort) on `tests/unit/verify/test_backpressure.py`
     -- pinned quarantine ~2 hours; every land in that window ran synchronous.
  2. `F401` (unused import) on `_lexical_selfcheck.py` / `_port_selfcheck.py`
     -- deadlocked T-2977 through FIVE land attempts. The ticket that FIXED
     those findings could not land because of the findings it fixed:
     quarantine blocked the drain, and the findings could not be filed because
     T-2977 already declared them (DuplicateFinding). A perfect circle.
  3. `I001` on `tests/test_narrative_migrate.py`
     -- cost T-3007 six land attempts and T-3011 four.
  4. `DOC006` on `tickets/T-3022/ticket.md`
     -- current, raised against a single-commit batch.

MEASURED COST: T-3007 needed 6 land attempts, T-3011 has now needed 5 and is
STILL unlanded despite being complete and committed. At 540s per timed-out
attempt that is roughly 90 minutes of pure waste on two tickets, plus every
other land in those windows running synchronously.

WHY THIS IS THE DOMINANT SYSTEMIC ISSUE: the individual findings are all real
and all trivial -- one unsorted import block, two unused imports, one doc
pointer. None of them indicates the repo is broken. But the RESPONSE to them is
maximal: disable the deferred-landing architecture for every agent in the fleet
until a human disposes of the finding by hand. The severity of the response is
completely decoupled from the severity of the trigger.

WHAT IS WANTED -- proportionality:

- A trivial, auto-fixable lint finding must not disable fleet-wide landing.
  Quarantine should gate on findings that indicate REAL BREAKAGE, not on
  anything that fires. Decide what the raise-worthy classes actually are and
  justify the cut.
- An UNATTRIBUTED finding (`commit=None, ticket=None`) is the specific shape
  that pins hardest, because attribution failure is what makes it undisposable
  by the normal path. Consider whether an unattributed trivial finding should
  raise at all, versus being recorded as debt for the sweep to file normally.
- If a finding IS auto-fixable, consider whether the system should fix and
  re-verify rather than halting the fleet and waiting for a human. Be careful:
  auto-fixing arbitrary findings is its own hazard, so scope any such path
  tightly to formatting-class rules with a deterministic fix.

DO NOT WEAKEN THE GUARDS THAT ARE CORRECT. This ticket is about the TRIGGER's
proportionality, not about relaxing verification:
- T-1703 (a truncated run is a DIFFERENT question, never a smaller answer) must
  stand.
- T-2929 (refuse to attribute against a stale baseline) must stand.
- The quarantine mechanism itself is sound -- a real regression SHOULD stop the
  fleet. The defect is that a doc pointer gets the same response as a real one.

ALSO IN SCOPE, the amplifier: quarantine currently requires a COORDINATOR to
notice and dispose by hand. All four occurrences today were cleared manually by
the coordinator after agents had already burned land attempts. There is no
surfacing -- an agent whose land times out has no way to learn that quarantine
is the cause. At minimum, a land that fails while quarantine is raised should
SAY SO in its refusal, naming the finding and the disposal command.

ACCEPTANCE
- A trivial auto-fixable finding of the four measured shapes above does NOT
  disable deferred landing fleet-wide. Must-stay-quiet fixture per shape.
- A finding representing real breakage STILL raises quarantine. Must-fire
  fixture -- do not solve this by never raising.
- A land that fails or refuses while quarantine is raised names quarantine as
  the cause, names the undisposed finding, and prints the disposal command.
- Report the measured land success rate before and after, under a comparable
  concurrent-agent load.
