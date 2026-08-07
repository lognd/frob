---
id: T-0337
title: capability resolver misses local rebinding of imported dangerous names (xyz
  = run; xyz(...))
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
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_single_rebind_detected
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_chained_rebind_detected
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_attribute_rebind_detected
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_benign_rebind_not_detected
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_parameter_shadow_still_not_detected
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_dangerous_then_benign_rebind_stays_detected
designated_repro_test: null
acceptance:
- text: given 'from subprocess import run\nxyz = run\nxyz(["pwned"])', when scan_file_capabilities
    runs, then it reports the exec capability (the local alias xyz resolves to subprocess.run)
  evidence: []
- text: given a chain 'from subprocess import run\na = run\nb = a\nb(["pwned"])',
    then exec is still reported (transitive copy-propagation within the scope)
  evidence: []
- text: 'given a safe rebinding ''run = lambda x: x\nrun(["ok"])'' (name bound to
    a non-dangerous value, no import), then NO capability is reported (a local def/assignment
    to a benign value must not false-positive), and a call through a name that is
    only EVER a parameter/local (never bound to a dangerous import) stays silent --
    the T-0328 shadowing guarantees must not regress'
  evidence: []
threat: elevation-of-privilege
component: null
---
Follow-on to T-0328 (import/binding-aware resolver). T-0328 resolves import aliases (import X as Y, from X import Z as W) but does NO intraprocedural dataflow, so a LOCAL rebinding of an imported dangerous name evades the scan. Empirically (2026-07-20): 'from subprocess import run; xyz = run; xyz(["pwned"])' -> scan reports [] (MISS); chained 'a = run; b = a; b(...)' -> [] (MISS); while direct/import-as/from-as all correctly report exec. This is a soundness hole in strata's 'may' analysis -- the exact 'you cannot get around it' property the tool exists to guarantee. FIX: add a scope-local copy-propagation pass to _capability.py's resolver -- when an assignment binds a name to (a) an import-table entry, (b) an attribute access that resolves to a dangerous target, or (c) another local name already known to alias a dangerous target, record name -> resolved_target; then resolve calls through those aliases (transitively, cycle-guarded). Keep it SOUND for may-analysis (over-approximate: if a name is ever bound to a dangerous target in the scope, calls to it may be dangerous) but do NOT regress T-0328's shadowing guarantees (a name that is a parameter/local bound ONLY to a benign value, or shadows an import with a non-dangerous binding, must stay silent). Reuse _py_import_table / _py_scope_bound_names / _resolve_py_expr rather than duplicating. Add litmus tests for: single rebind, chained rebind, rebind-then-call-via-attribute, benign rebind (no FP), parameter shadow (no FP, T-0328 regression guard), and reassignment where a name is first dangerous then rebound benign (document the may-analysis over-approximation choice).