## Done report

Tier-A auto-carry of split-carried INV006 waivers (T-1137/T-1134 child,
coordinator decision recorded on the ticket). `frob.gates._fix_engine.
fix_inv006_carried_waiver` is a new Tier-A handler: for every INV006
finding whose exclusivity-claim prose was moved VERBATIM out of a file
that already carries a covering `frob:waive INV006`
(`find_carried_waiver`, T-1134), it inserts that EXACT directive as the
new file's first line, in the source's own comment syntax (.py "#",
.rs "//"). Wired into `apply_tier_a_fixes` alongside the existing DOC007/
DOC002/TICK002 handlers.

Pairs with T-1176: `frob.gates._inv006_split_assist.find_carried_waiver`
now reads the source waiver edge's own `preset=` attr (not just its
resolved `reason=`) and, when present, builds the carried directive as
`frob:waive INV006 preset="<name>"` -- a preset REFERENCE, never a copy
of the resolved reason text, so a chain of carries can never silently
recreate the exact duplication T-1176's presets exist to remove. A
source waiver written with a plain inline reason= still carries its
literal reason text, unchanged from T-1134's original behavior.

The never-auto-waive anti-goal (T-1137) is preserved for every other
case: no verbatim match, or a match whose source only carries a bound
`frob:invariant` (not a waiver) -- both are left completely untouched,
covered by test_inv006_never_auto_waives_a_non_carried_finding.

CLI wiring (`frob check --fix`) remains out of scope here, same as
T-1138's own precedent -- `apply_tier_a_fixes` is ready for that later
batch to call directly.

### Changed
```
 design/frob.strata                     |   1 +
 docs/modules/gates.md                  |  32 +++++--
 src/frob/gates/_fix_engine.py          | 149 +++++++++++++++++++++++++++++++--
 src/frob/gates/_inv006_split_assist.py |  40 ++++++---
 src/frob/graph/_waive_presets.py       |  21 +++--
 tests/test_gates.py                    |  91 ++++++++++++++++++++
 tickets.md                             |  75 ++++++++++++++++-
 7 files changed, 372 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_waiver_verbatim_moved_from_waived_source` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_a_preset_reference_not_a_reason_copy` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_inv006_never_auto_waives_a_non_carried_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
