## Addendum 3 (three CONFIRMED vacuous consumers, not one)

Coordinator's own direct measurement, `frob.arch._layering._resolve_import_targets`
called on real first-party files:

    src/frob/tickets/_land_git_ops.py    specs=19   resolved=0
    scripts/verify_lands.py              specs=3    resolved=0

8 of the 19 specs for `_land_git_ops.py` are first-party (`frob.gitio`,
`frob.logging`, `frob.tickets._land_ledger_merge`,
`frob.tickets._land_merge_zones`, `frob.tickets._leases`,
`frob.tickets._models`, plus 2 more) -- not third-party noise being
correctly filtered. Import-based architectural layering analysis
therefore evaluates its rules against an EMPTY import set on this
repo's own tree. This is a claim about RESOLUTION being empty, not
that every layering rule produces zero findings by construction (a rule
using a different signal could still fire) -- but import-derived
layering cannot detect a violation it never sees an edge for.

Notably `scripts/verify_lands.py` resolves 0 here too, even though
`resolve_local_import` DOES resolve `scripts.fleet_status ->
scripts/fleet_status.py` when called directly on that one specifier --
meaning `_layering._resolve_import_targets` may add its OWN narrowing
on top of the primitive's defect, not simply inherit it. Establish
which when fixing: confirm whether fixing `resolve_local_import` alone
restores layering, or whether `frob.arch._layering` itself needs a
follow-up.

**Three confirmed vacuous consumers now, each independently measured
(not inferred from one shared root cause):**

1. Attribution (T-2156) -- `build_reference_graph_module_scoped` accepts
   no cross-file candidate; the T-2156 certifying evidence could not
   distinguish "fixed" from "cross-file resolution disabled".
2. Cycle detection (`frob cycle`, `src/frob/app/cycle_runner.py`) --
   positive control: an identical planted 2-file import cycle is found
   in a top-level layout and MISSED in the byte-identical src-layout
   copy. `frob cycle src/frob` reporting "no cycles found" across
   22,396 symbols on this repo's own tree proves nothing; it is
   structurally incapable of finding one here. Independently reproduced
   by two different agents (coordinator and implementer), same result.
3. Architectural layering (`frob.arch._layering`, `frob.arch._python`)
   -- confirmed above by direct call, not inference.

**Acceptance criteria addition**: the fix's acceptance must include a
must-still-pass / now-detects control for EACH of the three consumers
above, not only the primitive's own unit-level import-resolution
behavior:

- attribution: a genuine cross-file candidate resolves through
  `build_reference_graph_module_scoped` post-fix (a real positive
  case, not just "false positives stayed absent")
- cycle detection: `frob cycle` reports the SAME cycle for BOTH the
  top-level-layout and src-layout copies of the planted-cycle fixture
- architectural layering: `_resolve_import_targets` (or whatever the
  fixed call chain resolves through) returns a NON-empty resolved set
  for `src/frob/tickets/_land_git_ops.py`'s own real first-party
  imports, and a known layering violation (constructible the same way
  as the cycle control) is actually detected post-fix

A fix verified only at the `resolve_local_import` unit level does not
establish any of the three capabilities above actually came back --
this is the exact gap the coordinator's own T-2193 (filed on the T-2156
mis-certification) is about, generalized to every consumer of this
primitive.
