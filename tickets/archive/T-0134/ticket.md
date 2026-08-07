---
id: T-0134
title: frob.strata._facts hard 'import strata_core' crashes standalone installs with
  a design/ dir (found while working T-0133)
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_facts.py
- src/frob/strata/_parse.py
- src/frob/strata/_errors.py
- src/frob/strata/_design_load.py
- tests/unit/strata/test_facts.py
- tests/unit/strata/test_parse.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_facts.py::TestBuildFactsNativeExtensionUnavailable::test_build_facts_returns_native_extension_unavailable
- tests/unit/strata/test_parse.py::TestParseModuleNativeExtensionUnavailable::test_parse_module_returns_native_extension_unavailable
designated_repro_test: null
threat: null
component: null
---
T-0133 fixed frob.lang's guarded import of strata_core (_walk_strata.py) so standalone tool installs no longer crash on .strata source files. frob/strata/_facts.py (imported transitively by frob/strata/__init__.py -> _atomic.py -> _facts.py) still does a module-level 'import strata_core' with no guard, and raises ImportError itself (not even ModuleNotFoundError) if missing: 'strata_core native extension is required (charter D3: no pure-Python fallback); build it with make core'. This crashes frob check's sys_gate (frob/gates/__init__.py sys_gate -> frob.strata.load_design_ids) with an unhandled exception -- not a typed Result.Err -- for ANY repo that has a design/ directory, in a standalone (no frob-core/strata-core) tool install. Reproduced: uv tool install frob (bare, no --with natives) + a repo with design/*.strata content -> frob check crashes with a raw traceback instead of failing a gate cleanly. Charter D3 (no pure-Python fallback for strata semantics) may still hold for the actual facts/proof pipeline -- but the crash needs to become a typed Err (e.g. sys_gate should catch/skip with a clear degrade message) instead of an unhandled ImportError, matching frob.lang's T-0133 pattern.