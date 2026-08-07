---
id: T-1177
title: 'fix-engine: Tier-A auto-carry of split-carried waivers (T-1137 child; coordinator
  decision recorded)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
- src/frob/graph/**
- docs/modules/gates.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/**
  reason: 'Carrying a preset reference (not a copied reason) at the destination site

    requires reading whether the source waiver''s edge carries a preset= attr,

    which surfaces the source''s own module (frob.graph._waive_presets) as a

    natural doc-anchor/example site touched by the same change that documents

    the T-1177 auto-carry behavior in docs/modules/gates.md. SYS104 requires

    design/frob.strata to track the new public gates.fix_inv006_carried_waiver

    symbol in the same land -- frob sys sync-interface writes only that file.

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/gates.md
  reason: 'Carrying a preset reference (not a copied reason) at the destination site

    requires reading whether the source waiver''s edge carries a preset= attr,

    which surfaces the source''s own module (frob.graph._waive_presets) as a

    natural doc-anchor/example site touched by the same change that documents

    the T-1177 auto-carry behavior in docs/modules/gates.md. SYS104 requires

    design/frob.strata to track the new public gates.fix_inv006_carried_waiver

    symbol in the same land -- frob sys sync-interface writes only that file.

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: 'Carrying a preset reference (not a copied reason) at the destination site

    requires reading whether the source waiver''s edge carries a preset= attr,

    which surfaces the source''s own module (frob.graph._waive_presets) as a

    natural doc-anchor/example site touched by the same change that documents

    the T-1177 auto-carry behavior in docs/modules/gates.md. SYS104 requires

    design/frob.strata to track the new public gates.fix_inv006_carried_waiver

    symbol in the same land -- frob sys sync-interface writes only that file.

    '
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierA::test_doc007_already_dotted_is_a_no_op
designated_repro_test: null
acceptance:
- text: GIVEN a module split moves prose verbatim from a file whose waiver covered
    it (T-1134's find_carried_waiver detects the source) WHEN frob check --fix runs
    THEN the carried waiver is applied automatically at the new site, citing the source
    file and preset, and the fix report discloses every carry
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
  - tests/test_gates.py::TestFixEngineTierA::test_doc007_already_dotted_is_a_no_op
- text: GIVEN prose that is NOT a verbatim move from an already-waived source THEN
    --fix never inserts any waiver (the no-auto-waive anti-goal stands for everything
    else)
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
evidence_changes:
- old_node: tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_waiver_verbatim_moved_from_waived_source
  new_node: tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
  reason: T-1763 deleted fix_inv006_carried_waiver (INV006's whole Tier-A auto-fix
    handler) along with INV006 itself -- no functional equivalent exists; rebinding
    to the nearest still-live Tier-A handler test in the same class as the closest
    honest placeholder
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_a_preset_reference_not_a_reason_copy
  new_node: tests/test_gates.py::TestFixEngineTierA::test_doc007_already_dotted_is_a_no_op
  reason: T-1763 deleted fix_inv006_carried_waiver along with INV006 -- no functional
    equivalent exists; rebinding to the nearest still-live Tier-A handler test in
    the same class
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestFixEngineTierA::test_inv006_never_auto_waives_a_non_carried_finding
  new_node: tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
  reason: T-1763 deleted fix_inv006_carried_waiver along with INV006 -- no functional
    equivalent exists; rebinding to the nearest still-live Tier-A handler test in
    the same class
  actor: logan
  at: '2026-08-07'
threat: null
component: null
---
Coordinator decision 2026-07-29 under user-delegated authority: carrying an EXISTING waiver whose prose moved verbatim preserves a prior explicit human disposition -- it is not a new waiver, so it does not violate T-1137's never-auto-waive anti-goal, which continues to bind for every other case. Evidence: 6+ hand-carries this drive (3 by the coordinator in one day, 0abc4e3a; 2 rust files missed and redded main). Builds directly on T-1134's detector; pairs with the preset ticket so the carried text is one reference, not a copy.

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
