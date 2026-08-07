---
id: T-1087
title: wire VET-family/OPAQUE001 rule ids into registry known_rules + frob:enforces
  for 13 already-implemented SC-* detectors
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/design/registry/supply-chain.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes
- tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent
- tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_no_frob_enforces_edge_warns
designated_repro_test: null
threat: null
component: null
---
While reconciling T-0721's 39 deferred:T-0721 supply-chain.yaml entries,
13 were found to already have a real, live enforcing detector -- but
`docs/design/registry/_registry_exhaustiveness.py`'s REG002 check verifies
`handled_by:<rule-id>` against `_KNOWN_GATE_RULES | st.rule_ids`
(src/frob/gates/__init__.py), which does NOT include the `frob vet`
subsystem's own rule ids (VET001-VET011, VET-JS003, VET-PY00x, VET-RS00x,
etc. -- a different CLI surface, `frob vet`, not `frob check`'s gate
family). None of these VET-family ids currently resolve for a
`handled_by:` claim, and this ticket's own scope
(`src/frob/vet/**`, `docs/design/registry/supply-chain.yaml`) does not
cover `src/frob/gates/**`, where `_KNOWN_GATE_RULES` lives -- so widening
it is out of scope here and left for this follow-up.

The 11 entries whose enforcing rule is a VET-family id (left
`deferred:<this ticket>` in supply-chain.yaml rather than
`handled_by:`, pending this ticket):

- SC-ATTACK-TYPOSQUATTING -> VET-JS003 (frob.vet._typosquat, Damerau-
  Levenshtein distance vs the popular-package list)
- SC-DETECTION-EDIT-DISTANCE-NAME -> VET-JS003 (same detector)
- SC-ATTACK-INSTALL-SCRIPT-ABUSE -> VET002 (frob.vet._scan, undeclared
  install-hook capability observed vs declared)
- SC-DETECTION-MAINTAINER-INSTALLHOOK-NET -> VET002 (same detector,
  install-hook + network capability combination)
- SC-DETECTION-OBFUSCATED-SOURCE -> VET004 (frob.vet._obfuscation ensemble)
- SC-DETECTION-ENTROPY-BLOB -> VET004 (Shannon-entropy string-literal
  signal within the same ensemble)
- SC-DETECTION-TROJAN-SOURCE -> VET004 (bidi/zero-width Unicode signal
  within the same ensemble)
- SC-DETECTION-HEX-IDENTIFIER-RATIO -> VET004 (hex-identifier-ratio signal
  within the same ensemble)
- SC-DETECTION-QUARANTINE-WINDOW -> VET011 (frob.vet._scan, newly-published
  cooldown-window check)
- SC-DEFENSE-OSV -> VET005 (frob.vet._osv, osv-scanner adapter)
- SC-DETECTION-OSV-ADVISORY-MATCH -> VET005 (same detector)

Two more entries whose enforcing rule is OPAQUE001 (src/frob/gates/
_opaque.py, also out of this ticket's `src/frob/vet/**` scope for the
`frob:enforces` directive even though the rule itself IS in
`_KNOWN_GATE_RULES` already):

- SC-ATTACK-NATIVE-EXTENSION-OPACITY -> OPAQUE001 (a compiled/native
  extension import is a runtime-opaque construct OPAQUE001's deny-by-
  default already fires on)
- SC-DETECTION-PROC-MACRO-BUILDRS -> OPAQUE001 (a Rust proc-macro/build.rs
  is the same runtime-opacity class, frob.vet._capability_registry's
  `_OpaqueStructuralConstruct` already models it)

Plan: (1) add the 11 VET-family ids (or a namespaced subset alias) to
`_KNOWN_GATE_RULES`/the registry known-rules union so `handled_by:VET*`
resolves; (2) add `frob:enforces SC-...` directives at each entry's
emitting symbol (frob.vet._typosquat._find_typosquat, frob.vet._scan's
VET002/VET004/VET005/VET011 violation constructors, and
src/frob/gates/_opaque.py's OPAQUE001 emitter plus the
`_OpaqueStructuralConstruct`/native-extension capability_kind sites); (3)
flip all 13 supply-chain.yaml entries above from `deferred:<this ticket>`
to `handled_by:<rule>`, closing REG002/REG008 for them.