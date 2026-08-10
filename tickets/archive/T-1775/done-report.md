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
