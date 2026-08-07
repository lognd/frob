---
id: T-0432
title: 'vet: TS/JS computed (non-literal) bracket-subscript capability resolution'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_local_const_string_subscript_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_local_const_template_substitution_subscript_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_reassigned_const_string_subscript_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_non_literal_bound_subscript_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_multi_substitution_template_subscript_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_computed_subscript_not_detected
- tests/test_vet.py::TestCapabilityScanTsBindingResolution::test_interpolated_template_subscript_not_detected
designated_repro_test: null
threat: null
component: null
---
T-0377 reviewer round 2 found and fixed string-literal bracket access (obj['fn']) and dynamic import() evasions in the TS/JS binding-aware capability resolver, but a FULLY COMPUTED (non-string-literal) subscript -- ax[dynamicKey](url), require('axios')[someVar]() -- still resolves to None: the property name is a runtime value the static resolver cannot evaluate (documented as an accepted limitation, tested by test_computed_subscript_not_detected in tests/test_vet.py::TestCapabilityScanTsBindingResolution). This is a real evasion surface for a sufficiently motivated attacker (or heavily-minified/bundled code that routes dangerous calls through a computed property name). Candidates to close the gap: (a) a conservative fail-open heuristic -- if the OBJECT resolves to a known-dangerous import and the subscript is non-literal, flag the capability anyway (accepting some false positives on legitimate dynamic dispatch); (b) light dataflow to resolve the subscript expression when it is itself a simple string-valued local (const key = 'exec'; ax[key]()); (c) leave as a permanently documented honest limitation if the false-positive cost of (a) is judged too high. Needs a design decision before implementation, not just an extension of the existing exact-match resolver.