---
id: T-5394
title: 'test_lang_conformance_gate BehavioralCapabilityCheck: 30 params fail, css/scss/html/javascript/vue
  registry claims over capabilities the thin walkers do not behaviorally satisfy'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_support.py
- tests/test_lang_conformance_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35863437945 (ubuntu+macos, dev 08b02016db); re-verified failing on current dev tip: 30 parametrized tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[LANG-CAP] cases (css/scss/html/javascript/vue x call_graph/directive_parse/doc_extract/publicness/symbol_walk) plus test_directive_continuation_folds_correctly_not_just_present and test_real_registry_is_behaviorally_clean all fail with 'no behavioral fixture registered for language LANG' -- frob.lang._support.derive_capability_registry()'s _capability_symbol_walk_status/_capability_publicness_status/_capability_doc_extract_status/_capability_directive_parse_status/_capability_call_graph_status are BLANKET functions that mark every supported_languages() member IMPLEMENTED for all 5 capabilities uniformly (only call_graph has existing per-language NOT_APPLICABLE exemptions, for strata/bash). T-5300/T-5303 added css/scss/html/javascript/vue as thin, deliberately-narrow walkers (docs/modules/lang.md's own T-5300/T-5303 sections: 'none attempt full symbol-tree fidelity', 'plain CSS ... left unwalked by design') but neither ticket updated derive_capability_registry() to reflect what these thin walkers ACTUALLY behaviorally satisfy, nor added tests/test_lang_conformance_gate.py's own per-language _CAPABILITY_FIXTURE_SOURCES entries. Fix requires reading docs/modules/lang.md's T-5300/T-5303 sections and each walker (_walk_css.py/_walk_html.py/_walk_javascript.py/_walk_vue.py) to judge, per (language, capability) cell, whether the capability is genuinely IMPLEMENTED (needs a real fixture added to the test) or should be NOT_APPLICABLE/KNOWN_GAP (needs a per-language exemption added to the relevant _capability_*_status function, following the existing strata/bash call_graph precedent) -- this is a design judgment call per the coordinator's own framing, not a blanket skip.