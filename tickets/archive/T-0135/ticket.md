---
id: T-0135
title: sys_gate imports frob.strata (and its unguarded strata_core dep) before the
  design/ opt-in check -- crashes frob check on ANY repo in a standalone install (supersedes/extends
  T-0134)
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
- .github/workflows/ci.yml
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSysGate::test_no_design_dir_never_imports_frob_strata
- tests/test_gates.py::TestSysGate::test_design_dir_degrades_with_typed_error_on_native_extension_missing
- tests/test_gates.py::TestSysGate::test_default_design_dir_mirror_stays_in_sync
designated_repro_test: null
threat: null
component: null
---
Root cause found while verifying T-0133's CI degrade job: frob/gates/__init__.py's sys_gate() does 'from frob.strata import load_design_ids' as its FIRST statement, before the 'if not (root/design_dir).is_dir(): return ()' opt-in check below it. frob.strata.__init__ transitively imports frob/strata/_facts.py, which does an unguarded module-level 'import strata_core' and raises ImportError immediately if absent (charter D3: no pure-Python fallback, intentional -- but the crash should not be reachable for repos that never opted into a design/ directory at all). Net effect: 'frob check' crashes with a raw traceback on EVERY repo in a standalone (uv tool install frob, no --with natives) install, not just ones using strata design files -- reproduced locally building the wheel with 'uv build --wheel', installing into a clean venv, and running frob check against a fixture repo with no design/ dir. Fix: move the 'from frob.strata import load_design_ids' import inside sys_gate to after the design_dir existence check (or make it lazy/guarded), so repos that never touch design/ never pay the strata_core import cost. T-0134 (already filed) covers making frob.strata._facts's own crash a typed Err for repos that DO use design/ files without the native parser -- this ticket is the more urgent half: repos that don't use design/ at all must never hit frob.strata's import machinery.