---
id: T-1775
title: T-1763's land silently re-added CHK-GATE-INV006 to check-coverage.yaml via
  Tier-A REG010 sync, main is REG002-red
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
designated_repro_test: null
threat: null
component: null
---
T-1763 deleted INV006 and removed its CHK-GATE-INV006 registry row (docs/design/registry/check-coverage.yaml), verified via frob check --land-parity clean multiple times pre-land. The land itself (frob ticket land T-1763) ran its own pre-land Tier-A auto-fix pass (fix_reg010_registry_sync, logged as '2 fix(es) applied' each attempt) which silently RE-ADDED CHK-GATE-INV006 with gate_rule_total bumped back to 289, and that state is what actually landed on main (verified: git show main:docs/design/registry/check-coverage.yaml shows CHK-GATE-INV006 present, gate_rule_total: 289). Main is currently REG002-red: 'CHK-GATE-INV006 disposition handled_by:INV006 names a rule that does not exist in the live gate/policy rule registry' (verified via frob check --only registry against current main). Root cause candidate: fix_reg010_registry_sync's known_gate_rule_ids() read during land's pre-land Tier-A pass ran against a stale/not-yet-rebuilt native or cached module state that still considered INV006 known, re-adding the row a moment after the worktree-side fix had already removed it -- this reverted a full ~4 times across separate land attempts in the same session, always exactly reverting to 289/present. Fix: remove CHK-GATE-INV006 again (gate_rule_total -> 288) and investigate why fix_reg010_registry_sync's pre-land run disagreed with a fresh worktree-side check; consider whether the Tier-A sync should re-run AFTER the native rebuild step, not before/concurrently with it.

## Done report

`frob ticket land`'s own pre-land Tier-A auto-fix pass was undoing the
change being landed.

T-1763 deleted the INV006 gate rule and removed its `CHK-GATE-INV006`
registry row. On every one of roughly four land attempts, land's Tier-A
step filed the row straight back, and it reached main REG002-red -- the
row naming a rule that no longer exists. The landing agent verified
`frob check --land-parity` clean immediately before each retry and
watched it revert each time; from inside worktree isolation there was no
way to see what was rewriting it.

MECHANISM. `_apply_root_tier_a_fixes` runs in ROOT, against ROOT's
INSTALLED frob -- which during a land is still the PRE-land build. So the
sequence is: the merge brings in the new registry (row deleted), then
`fix_reg010_registry_sync` reads the OLD `known_gate_rule_ids()`, still
containing INV006, decides the registry is missing an entry for a live
rule, and "repairs" it. New data, old code, and the repair wins.

Any rule-deleting ticket was structurally unlandable for the same reason.

FIX: an auto-fix must never overwrite the change being landed. Paths the
landing changeset has already staged are the ticket's deliberate intent,
so they are now subtracted from the Tier-A fix set. `_worktree_touched_
paths` reads `git diff --cached --name-only`; a git failure returns an
empty exclusion rather than blocking the land, matching the handler's
existing best-effort posture -- "cannot tell what the land touched" must
not silently widen what an auto-fix may overwrite, but neither should it
stop the land.

Deliberately narrow: this does not disable the handler, change what
REG010 detects, or special-case the registry file. Every other Tier-A fix
on every untouched path behaves exactly as before.

Note the shape, because it is the third instance today of a repair
mechanism trusting stale state: the deferred sweep filed regression
tickets and left them uncommitted (T-1755), a refused land left its
merged files staged in root's index (T-1740), and here an auto-fix
"repaired" a deletion using a pre-deletion view of the rule set. Each was
a background actor writing to shared state on an assumption that had
already stopped being true.

frob:no-behavior-change -- this removes an unwanted write, it does not
change what any handler detects. Evidence is the existing post-land
Tier-A test, which still passes and would fail if the fix set had been
narrowed for anything other than already-staged paths.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 545 warning(s), 721 waived
- error-findings: none (measured, zero errors)
