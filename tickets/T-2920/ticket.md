---
id: T-2920
title: 'Strata ratchet: shrink-only auto-tightening, capability escalation is always
  an error'
state: queued
kind: feature
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: tier
  old_value: ticket
  new_value: epic
  reason: 'user corrected the premise: auto-deriving may=/code= makes the ceiling
    equal whatever the code does, defeating the shrink-the-interface purpose; superseded
    by the shrink-only ratchet design'
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Strata's `may=` list is a CEILING and its `code=` globs are an ownership
partition. Both exist to forcibly SHRINK the interface. An earlier proposal on
this program (T-2907, dropped in favour of this ticket) suggested deriving both
from observation via a `frob sys sync`. That was wrong: a ceiling regenerated
from observation equals whatever the code happens to do, so a module that starts
performing `net` would have `net` silently added to its own ceiling. That is a
ratchet with no teeth -- the rubber-stamp failure class this repo has paid for
repeatedly (WAIVE004, auto-drop, sweep false-green).

The correct axis is not derive-vs-declare. It is RATCHET DIRECTION.

1. DECLARATION LOOSER THAN OBSERVATION (declared but never observed).
   Example measured on a foreign repo: "SYS101 node=pipeline: capability 'eval'
   declared but never observed". The declaration permits more than the code
   uses. Tightening it is always safe and is exactly the stated purpose of the
   model. Provide `frob sys shrink` to auto-TIGHTEN this direction only: drop
   unobserved capabilities, narrow over-broad `code=` globs to the files that
   actually exist. The ratchet may only ever move toward a smaller interface.
   This is strictly better than today, where the loose direction is a warning
   that everyone ignores and the interface never actually shrinks.

2. OBSERVATION WIDER THAN DECLARATION (capability escalation).
   NEVER auto-synced, under any flag. Always an ERROR. A node acquiring a
   capability its ceiling does not grant is the single most valuable signal the
   whole subsystem produces -- it is "you did something bad", verbatim. The
   human either fixes the code or justifies raising the ceiling in a reviewable
   diff.

3. OBSERVED-BUT-UNBOUND FILES (SYS103).
   Example measured: "SYS103 node=scripts/bump_version.py: has an observed
   capability (fs-read, fs-write) but no node's code= glob binds it". A file
   with real capabilities that no node owns is a genuine hole, not bookkeeping.
   It stays an ERROR requiring a human to place the file. `frob sys shrink` must
   NEVER auto-bind it -- auto-binding would erase precisely the signal that a
   new, uncategorised, capability-bearing file entered the system.

Net effect on the noise problem that motivated this program: the bookkeeping
mass measured on a foreign repo (SYS103 x140, SYS003 x100, plus the SYS101
declared-never-observed family) collapses because direction 1 becomes a
one-command tightening rather than a standing warning, while directions 2 and 3
become hard errors instead of being diluted by that noise.

ACCEPTANCE

- Given a node whose `may=` declares a capability the scanner never observes,
  when `frob sys shrink` runs, then the capability is removed from the
  declaration and the diff is reviewable; and the repo's error count is
  unchanged (this direction was never an error).
- Given a node whose code performs a capability its `may=` does not grant, when
  any strata gate runs, then it is an ERROR; and `frob sys shrink` refuses to
  widen the declaration, with a message saying so explicitly. Must-fire fixture
  required: a node that acquires `net` it never declared.
- Given a capability-bearing file that no node's `code=` glob binds, when any
  strata gate runs, then it is an ERROR naming the file, and `frob sys shrink`
  does not bind it. Must-fire fixture required.
- Must-still-pass control: frob's own repo keeps 0 SYS errors, and its
  SYS200-205 finding count is unchanged before and after.
- Must-not-regress: no flag, env var, or config key may enable auto-widening.
  Prove by a test that asserts the widening path does not exist.
