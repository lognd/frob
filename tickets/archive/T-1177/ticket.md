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
- tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_waiver_verbatim_moved_from_waived_source
- tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_a_preset_reference_not_a_reason_copy
- tests/test_gates.py::TestFixEngineTierA::test_inv006_never_auto_waives_a_non_carried_finding
designated_repro_test: null
acceptance:
- text: GIVEN a module split moves prose verbatim from a file whose waiver covered
    it (T-1134's find_carried_waiver detects the source) WHEN frob check --fix runs
    THEN the carried waiver is applied automatically at the new site, citing the source
    file and preset, and the fix report discloses every carry
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_waiver_verbatim_moved_from_waived_source
  - tests/test_gates.py::TestFixEngineTierA::test_inv006_carries_a_preset_reference_not_a_reason_copy
- text: GIVEN prose that is NOT a verbatim move from an already-waived source THEN
    --fix never inserts any waiver (the no-auto-waive anti-goal stands for everything
    else)
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_inv006_never_auto_waives_a_non_carried_finding
threat: null
component: null
---
Coordinator decision 2026-07-29 under user-delegated authority: carrying an EXISTING waiver whose prose moved verbatim preserves a prior explicit human disposition -- it is not a new waiver, so it does not violate T-1137's never-auto-waive anti-goal, which continues to bind for every other case. Evidence: 6+ hand-carries this drive (3 by the coordinator in one day, 0abc4e3a; 2 rust files missed and redded main). Builds directly on T-1134's detector; pairs with the preset ticket so the carried text is one reference, not a copy.