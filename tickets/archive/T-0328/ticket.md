---
id: T-0328
title: 'capability scanner: import/binding-aware symbol resolution, not evadable substring
  needles'
state: done
kind: security
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_registry.py
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_import_as_alias_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_from_import_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_from_import_as_detected_with_correct_kind
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_import_as_alias_operation_names_registry_entry
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_method_shadowing_import_not_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_param_shadowing_import_not_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_local_variable_shadowing_import_not_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_bare_name_call_with_no_import_not_detected
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_direct_call_still_detected_via_resolver
- tests/test_vet.py::TestCapabilityScanBindingResolution::test_attribute_only_env_access_via_alias_detected
designated_repro_test: null
acceptance:
- text: given 'import subprocess as sp' then 'sp.run(x)', when scanned, then exec
    is observed (alias resolved to subprocess.run) -- currently MISSED
  evidence: []
- text: given 'from subprocess import run' then 'run(x)', when scanned, then exec
    is observed (from-import resolved) -- currently MISSED
  evidence: []
- text: given 'from os import system as e' then 'e(x)', when scanned, then exec is
    observed (NOT eval) -- currently WRONG kind
  evidence: []
- text: given a LOCAL binding shadowing an import (a class method or var named 'run',
    a param 'system'), when scanned, then the dangerous kind is NOT observed -- scope-aware,
    no false positive
  evidence: []
- text: given re-export chains and attribute access on a shadowed name (x.subprocess.run
    where subprocess is an unrelated attribute), then it does not falsely fire
  evidence: []
threat: elevation-of-privilege
component: null
---
CONFIRMED live 2026-07-19: frob.vet._capability is fundamentally a lexical substring/needle matcher (even after T-0308 comment/word-boundary hardening). It only matches the LITERAL qualified form in the registry needle (e.g. 'subprocess.run('), so it is EVADED by ordinary Python: 'import subprocess as sp; sp.run()' -> MISSED; 'from subprocess import run; run()' -> MISSED; 'from os import system as e; e()' -> reported 'eval' not 'exec'. This is an ELEVATION-OF-PRIVILEGE soundness hole -- a node can genuinely exec/net/ffi while the scanner observes nothing, so SYS100 never flags the undeclared capability, and a developer (lazy OR malicious) dodges the 'may' declaration just by aliasing an import. FIX: replace/augment the lexical match with real import/binding-aware resolution using the existing tree-sitter parse (frob.lang). Per language: (1) build the module's IMPORT/BINDING TABLE -- import X, import X as Y, from X import Z, from X import Z as W (python); the analogous forms for TS (import {x} from, import * as, require), rust (use path::to::item, use ... as), c/c++ (#include is coarse -- keep needles there but note the limit). (2) For each call/attribute site, resolve the leftmost name through the binding table (and enclosing scope) to its ORIGIN, reconstruct the fully-qualified target (sp.run -> subprocess.run; run -> subprocess.run), and match the registry by RESOLVED IDENTITY (module + attribute path), not raw text. (3) SCOPE-AWARENESS is mandatory to avoid FALSE POSITIVES: a local binding (param, assignment, class method, nested def) SHADOWS an import of the same name -- 'Job().run()' or a param 'system' must NOT resolve to the dangerous symbol. The registry likely needs a resolvable (library, symbol) key alongside the display needle. Python is the priority (highest coverage); design the resolver so TS/rust plug in. Keep the comment/string-exclusion + word-boundary guards. LITMUS: every evasion case above now detected; every shadowing case NOT detected; no new false positive on frob's own tree (frob check --only sys / capability tests unchanged); the exhaustiveness meta-test still green. This is the 'actually parse the symbols and see if they refer to what they match' upgrade.