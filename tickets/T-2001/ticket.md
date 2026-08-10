---
id: T-2001
title: Tier-A auto-fixes design/frob.strata but not the capability ratchet lock, so
  half the obligation self-heals and the breach surfaces on an unrelated later land
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED: bit TWICE within one hour on 2026-08-10, two different agents,
same file pair.

The capability ratchet has TWO places that must agree:
1. `design/frob.strata` -- the via-list entries granting a capability.
2. `docs/design/registry/capability-via-ratchet.lock.json` -- the
   committed ceiling SYS111 compares against.

`fix_sys100_may_via_union` / `fix_sys100_extended_whole_node_grant`
(registered in `TIER_A_HANDLERS`, `src/frob/gates/_fix_engine.py:540`)
auto-fix place 1 at every land. NOTHING auto-fixes place 2. So the
auto-fix silently satisfies half the obligation and leaves the other
half stale, which is worse than fixing neither -- the land goes green
and the ceiling breach surfaces on some LATER, unrelated ticket's land.

Occurrence 1: T-1977 wired `capability_ratchet_violations` as SYS111 and
had to re-baseline three drifts in `design/frob.strata` BY HAND
(`graphlang::fs.read` 7>6, `testsuite::exec` 159>158,
`testsuite::fs.write` 301>297).
Occurrence 2: T-1665 added `tests/unit/gates/test_refs.py`, whose
git-subprocess and tmp_path-write fixtures needed exec/fs.write via-list
entries. `design/frob.strata` was updated; the lock JSON was not.
SELFAUDIT001 went red on main and was repaired by a separate hand commit,
`7e5bd86c2` (6 insertions, 6 deletions, lock JSON only). An auto-filed
post-land sweep ticket (T-2000) had to be filed and then dropped to
account for it.

Note the shape: T-1665's agent did nothing wrong. It was landing a
REF001 rewrite and had no reason to know that adding a test file with a
tmp_path fixture obligates a JSON ceiling bump in a registry directory.

This is the exact pattern T-1974 already established and closed once for
a different rule: when one of N parallel bookkeeping obligations keeps
regressing while its siblings do not, find the auto-fix the siblings
have and it lacks, rather than adding a new gate over all of them. REG010
and DOCENUM001 both self-heal at land time for this reason. The ratchet
lock is the remaining sibling with no handler.

## Do not fix it this way
- Do NOT add a gate/refusal that tells the author to bump the lock. A
  refusal makes the author fix it every time; an auto-fix makes it stop
  happening. The correct edit here is mechanically derivable from the
  real capability sites, exactly like `fix_reg010_registry_sync`'s is.
- Do NOT have the handler bump the ceiling unconditionally to whatever
  it observes. That converts the ratchet into a no-op that ratifies any
  growth, which destroys the entire point of a ratchet. It must only
  re-baseline growth that the SAME land's own diff demonstrably causes,
  and must record the reason -- widening beyond that stays a human
  decision, as T-1977 treated it.
- Do NOT fix it by telling agents to check the lock file. That is a
  process rule, and a process rule is not an enforcement.

## Acceptance criteria
1. A test that FAILS FIRST: a land whose diff adds a new capability site
   (e.g. a test file using a tmp_path write fixture) leaves
   `capability-via-ratchet.lock.json` stale under current code, and
   SELFAUDIT001 goes red on the NEXT unrelated land. Assert the red.
2. A Tier-A handler bumps the lock in the same land as the strata
   via-list change, so both places move together or neither does.
3. Growth NOT attributable to the landing diff must still fail rather
   than be silently ratified -- assert this explicitly with a case where
   the ceiling is already exceeded before the land begins.
