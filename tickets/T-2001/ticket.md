---
id: T-2001
title: Tier-A auto-fixes design/frob.strata but not the capability ratchet lock, so
  half the obligation self-heals and the breach surfaces on an unrelated later land
state: done
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
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- docs/design/registry/capability-via-ratchet.lock.json
- docs/modules/gates.md
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: registering the new handler in TIER_A_HANDLERS (lives in _fix_engine.py),
    plus its test coverage; lock.json is the file the fix writes to, needed for a
    real end-to-end test
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gates.py
  reason: registering the new handler in TIER_A_HANDLERS (lives in _fix_engine.py),
    plus its test coverage; lock.json is the file the fix writes to, needed for a
    real end-to-end test
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: registering the new handler in TIER_A_HANDLERS (lives in _fix_engine.py),
    plus its test coverage; lock.json is the file the fix writes to, needed for a
    real end-to-end test
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/gates.md
  reason: documenting the new Tier-A handler alongside its siblings
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/__init__.py
  reason: the _KNOWN_RULE_FIXABILITY checked-in literal drift-locks against TIER_A_HANDLERS
    and needs a SYS111 entry too
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
- tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched
- tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op
- tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule
designated_repro_test: tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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

## Done report

Read T-1974 (the DOCENUM001/REG010 precedent) first, per the ticket's own
instruction: the shape is "one of N parallel bookkeeping obligations
self-heals, its sibling does not" -- add the missing sibling Tier-A
handler, never a new gate/refusal telling the author to fix it by hand.

Mechanism: fix_sys100_may_via_union/fix_sys100_extended_whole_node_grant
(TIER_A_HANDLERS, src/frob/gates/_fix_engine.py) already auto-widen
design/frob.strata's via-lists at every land. Nothing auto-updated
docs/design/registry/capability-via-ratchet.lock.json's committed
accepted_count ceiling SYS111 (capability_ratchet_violations,
frob.strata._effects) compares against -- so the SYS100 auto-fix
silently satisfied half the obligation and the ceiling breach surfaced
on a LATER, unrelated land's SYS111 check (T-1977, T-1665, both
measured in the ticket body).

Fix: new Tier-A handler fix_sys111_capability_ratchet_sync
(src/frob/gates/_fix_engine_sync.py), registered in TIER_A_HANDLERS
(src/frob/gates/_fix_engine.py) immediately AFTER "SYS100" in dict
order -- apply_tier_a_fixes' own docstring says dict order is call
order, so by the time this handler runs, design/frob.strata already
reflects whatever SYS100 just widened in the SAME pass.

Explicitly does NOT bump the ceiling unconditionally to whatever is
observed (the ticket's own named anti-goal: that would turn the ratchet
into a no-op that ratifies any growth). Instead it measures growth
attribution against a BEFORE snapshot: design/'s content at `git show
HEAD`, materialized into a scratch dir via `git archive` and loaded
through the EXACT SAME load_design_ids/merge_models pipeline the live
model uses (no second, parallel strata-parsing implementation over git
blob text) -- new helper _capability_counts_at_head. A (node, atom) pair
is bumped ONLY if its CURRENT count exceeds the committed ceiling AND
grew since HEAD; a pair already exceeding the ceiling but UNCHANGED
since HEAD is a pre-existing breach and is left violating -- exactly
acceptance criterion 3 ("growth NOT attributable to the landing diff
must still fail rather than be silently ratified"). Every bump records
a `reason` naming the before/after counts and "ticket": "T-2001" in the
lock entry itself, the same accountability the lock's own module
docstring already demands of a human-authored widening.

Verified manually end-to-end with two throwaway real git repos before
writing the formal pytest tests (both reproduced in the Done report's
own investigation, repeated here for the record):
  repo1: 1 via site, ceiling=1, committed. Widened via-list to 2 sites
  (uncommitted, simulating SYS100's own fix). Ran the handler:
  applied=[SYS111 Api::fs.write 1->2], lock file's accepted_count now 2
  with a recorded reason.
  repo2: 3 via sites, ceiling stuck at 1, ALL committed together (no
  uncommitted diff at all). Ran the handler: applied=[] -- ceiling left
  at 1, capability_ratchet_violations still reports the violation.

Disclosed, NOT hidden, first-cut gap (named in both the handler's own
docstring and docs/modules/gates.md): a hand-edited via-list widening
the agent already COMMITTED on their own worktree branch before landing
is invisible to this HEAD-relative diff, since HEAD already includes
it. Both measured occurrences (T-1977, T-1665) were caused by SYS100's
OWN auto-fix widening an UNCOMMITTED via-list in the SAME Tier-A pass,
which this fully covers. Closing the committed-hand-edit case
completely would need a true pre-land-tip base ref threaded through
TIER_A_HANDLERS' uniform call shape (the same shape frob.tickets._land.
land's sync_gate_rules callback already uses) -- a larger, separate
change than this ticket's own scope, not smuggled in.

Also fixed two checked-in-literal drift-locks the new TIER_A_HANDLERS
entry tripped (both were already-existing tests, not new ones I wrote):
tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule
(added "SYS111" to the expected set) and
tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
(added "SYS111": "auto" to src/frob/gates/__init__.py's
_KNOWN_RULE_FIXABILITY). Also satisfied AFFECT001 (TIER_A_HANDLERS'
changed affects()-closure doc target) by adding a full subsection to
docs/modules/gates.md's Tier-A section plus the frob:describes
directive.

Full tests/test_gates.py (708 tests) passes.

BUG002 note: the designated repro test is a brand-new node, absent at
parent -- --check-repro correctly returns NO_VERDICT/exit 5 (collection
error, the function itself is new). Designated via
--designate-repro-force with the manual fail/pass verification above
recorded as the substitute evidence, per the documented T-1929
structural-NO_VERDICT shape.

### Changed
```
 tickets/T-2001/ticket.md | 47 +++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 45 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_leaves_a_pre_existing_breach_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, DSL001@CHANGELOG.md, DUP001@tests/test_gates.py, F401@/home/logan/projects/frob/.claude/worktrees/ratchet-ceiling/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2001
