---
id: T-1404
title: Wire frob ticket land's pre-fix pass to FMT001's new only_paths land-scoping
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_out_of_scope_file_with_noncanonical_directive_is_left_untouched
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_in_scope_file_with_noncanonical_directive_is_still_fixed
designated_repro_test: null
threat: null
component: null
---
T-1391 added `fix_fmt001_directive_wrap`'s `only_paths` keyword-only
parameter (src/frob/gates/_fix_engine.py), which restricts FMT001's
Tier-A rewrite to a caller-supplied set of root-relative paths instead
of walking the whole tree. `only_paths=None` (unset) still preserves the
original whole-tree behaviour, so nothing changed for a standalone
`frob check --fix` or for `frob ticket land`'s existing pre-land
absorption call -- `_absorb_pre_land_fixes` in
src/frob/app/ticket_runner/_land_cmd.py still calls `apply_tier_a_fixes`
with no scoping at all, so the land-scope-discipline collision T-1391
diagnosed (FMT001's pre-fix pass mechanically rewriting frob:waive
reason comments in files outside the landing ticket's declared scope)
is only half fixed: the mechanism exists but nothing in a real land
invokes it yet.

This ticket is that wiring: `_absorb_pre_land_fixes` needs to compute
the landing ticket's touched-file set (git diff of the worktree against
main, or the ticket's declared scope globs resolved to real paths --
whichever this repo's other diff-scoped gates, e.g. FMT001 itself,
already use as their own touched-set source) and pass it through to
`apply_tier_a_fixes` -> the FMT001 lambda in `TIER_A_HANDLERS` ->
`fix_fmt001_directive_wrap`'s `only_paths`.

Scope note: touching `_land_cmd.py` alone was ruled out of T-1391's own
scope during that ticket's work -- `frob ticket scope --add` on it
surfaced a cascade of scope-closure warnings pulling in
`_land_cmd.py`'s own private helpers across
src/frob/app/ticket_runner/__init__.py, _verify.py, and _close_cmd.py.
Whoever takes this should scope narrowly to just the touched-set
computation and the one `apply_tier_a_fixes` call site, and expect to
either satisfy or explicitly waive those same closure warnings.

Acceptance:
- GIVEN a land whose ticket scope excludes a file elsewhere in the tree
  carrying a non-canonical frob: directive, WHEN `frob ticket land` runs
  its Tier-A pre-fix pass, THEN that out-of-scope file is left untouched
  (this is T-1391's own acceptance [0], only actually closed end-to-end
  once this ticket lands).
- GIVEN the same land, WHEN a file genuinely inside the landing ticket's
  touched set carries a non-canonical frob: directive, THEN it is still
  fixed exactly as before.