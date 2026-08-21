---
id: T-2410
title: walk_strata hardcodes RawSymbol.public=True (no real publicness semantics)
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_strata.py
- src/frob/lang/_support.py
- docs/modules/lang.md
- tests/unit/test_lang_strata.py
evidence_scope:
- tests/test_lang_conformance_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/_support.py
  reason: the ticket's own plan requires flipping _capability_publicness_status's
    strata KNOWN_GAP to IMPLEMENTED once the real clearance-derived publicness rule
    lands in _walk_strata.py -- the two are one indivisible change (a real rule with
    the registry still claiming KNOWN_GAP is a lie in the other direction)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/lang.md
  reason: _support.py's capability-status docstrings/constants carry frob:doc edges
    into docs/modules/lang.md; flipping strata publicness KNOWN_GAP->IMPLEMENTED needs
    that doc's own strata note updated in the same change
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_lang_strata.py
  reason: test_all_symbols_are_public locks in the OLD public=True-for-everything
    placeholder this ticket replaces with real clearance-derived publicness; must
    update to assert the mixed True/False shape chirp.strata's own clearance clauses
    now produce
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_lang_strata.py::TestParseStrata::test_publicness_is_derived_from_clearance_not_a_blanket_true
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[strata-publicness]
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_every_registered_language_is_covered
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean
designated_repro_test: tests/unit/test_lang_strata.py::TestParseStrata::test_publicness_is_derived_from_clearance_not_a_blanket_true
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d857690f0bf31ed22cc93060cc0ae60ce1789a39
---
T-2365's behavioral capability conformance suite (tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck) caught this: frob.lang._walk_strata.py:277 sets public=True unconditionally for every strata symbol, regardless of the construct's real clearance/visibility (design/litmus/chirp.strata's own fixtures declare 'clearance Public' on some nodes, implying a real visibility concept exists in the surface syntax that the walker does not read). This makes CAPABILITY_PUBLICNESS a KNOWN_GAP for strata (frob.lang._support._capability_publicness_status), not IMPLEMENTED -- a placeholder True is not language-correct publicness the way T-0841's per-grammar rule is for every other adapter. Wire a real publicness rule (likely keyed on clearance/visibility surface syntax) or make the KNOWN_GAP explicit and permanent if strata genuinely has no such concept.