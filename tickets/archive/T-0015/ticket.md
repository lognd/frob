---
id: T-0015
title: Implement per-rule severity overrides in frob.toml (gates currently hardcodes
  severity in code)
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage
- tests/test_gates.py::TestSeverityOverrides::test_no_frob_toml_is_identity
designated_repro_test: null
threat: null
component: null
---
docs/modules/gates.md's rule catalog states severity is 'per-rule default overridable in frob.toml', but src/frob/gates/__init__.py's own Phase 4 implementation notes say this was explicitly scoped out: severities are fixed constants in code (ERROR for DRIFT/COV002-004/SCOPE001/PRE001/INV001-002/TEST001/TEST004/WAIVE001; WARN for COV001/TODO001/TEST002/003/005), and frob.toml has no [rules] or per-rule table read anywhere in the gates loading path. This was discovered while trying to set a legacy-adoption severity baseline (TEST001/TEST004/TEST006 -> warn) for the dogfood milestone: writing such config to frob.toml would be silently ignored, so no baseline was written. Implement real per-rule severity override support (e.g. a [rules] table in frob.toml, read in run_gates, applied when constructing each Violation) so this baseline can actually be set.