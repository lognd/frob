---
id: T-0015
title: Implement per-rule severity overrides in frob.toml (gates currently hardcodes
  severity in code)
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
evidence:
- tests/test_gates.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage
- tests/test_gates.py::TestSeverityOverrides::test_no_frob_toml_is_identity
attachments: []
---
docs/gates.md's rule catalog states severity is 'per-rule default overridable in frob.toml', but src/frob/gates/__init__.py's own Phase 4 implementation notes say this was explicitly scoped out: severities are fixed constants in code (ERROR for DRIFT/COV002-004/SCOPE001/PRE001/INV001-002/TEST001/TEST004/WAIVE001; WARN for COV001/TODO001/TEST002/003/005), and frob.toml has no [rules] or per-rule table read anywhere in the gates loading path. This was discovered while trying to set a legacy-adoption severity baseline (TEST001/TEST004/TEST006 -> warn) for the dogfood milestone: writing such config to frob.toml would be silently ignored, so no baseline was written. Implement real per-rule severity override support (e.g. a [rules] table in frob.toml, read in run_gates, applied when constructing each Violation) so this baseline can actually be set.

## Done report

Implemented [gates.severity] frob.toml table; applied as a
post-processing step in run_gates (_apply_severity_overrides) so every
gate stays pure and there is exactly one override site. Garbage values
are logged and ignored. docs/gates.md severity paragraph now true.
