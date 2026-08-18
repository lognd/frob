---
id: T-2410
title: walk_strata hardcodes RawSymbol.public=True (no real publicness semantics)
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_walk_strata.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2365's behavioral capability conformance suite (tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck) caught this: frob.lang._walk_strata.py:277 sets public=True unconditionally for every strata symbol, regardless of the construct's real clearance/visibility (design/litmus/chirp.strata's own fixtures declare 'clearance Public' on some nodes, implying a real visibility concept exists in the surface syntax that the walker does not read). This makes CAPABILITY_PUBLICNESS a KNOWN_GAP for strata (frob.lang._support._capability_publicness_status), not IMPLEMENTED -- a placeholder True is not language-correct publicness the way T-0841's per-grammar rule is for every other adapter. Wire a real publicness rule (likely keyed on clearance/visibility surface syntax) or make the KNOWN_GAP explicit and permanent if strata genuinely has no such concept.