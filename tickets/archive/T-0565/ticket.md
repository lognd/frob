---
id: T-0565
title: 'DEAD001 burndown: triage 51 findings, most likely false-positive classes (module-level
  dict refs, pytest fixtures, pydantic validators)'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- tests/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
- tests/test_lang.py::TestParsePython::test_private_module_level_const_extracted
- tests/unit/test_dup_cache.py::TestConnectionReuse::test_close_all_drops_cached_connections
- tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_names_registry_entry
designated_repro_test: null
threat: null
component: null
---
frob check --only dead_symbols reports 51 DEAD001 warnings on this repo (Python-only
pass, T-0422). Manual triage of all 51 found two systematic FALSE-POSITIVE classes,
not real dead code, both structural gaps in frob.graph.callgraph's substrate:

1. ~40/51: a private symbol referenced ONLY from a module-level dict/tuple literal
   (e.g. `_DISPATCH_BY_TYPE = {"cpp": _dispatch_check_cpp, ...}` in
   src/frob/app/check_runner.py, `_WALKERS = {"python": _walk_python, ...}` in
   src/frob/lang/_extract.py, PII/secrets pattern-registry tuples). frob.lang's
   RawSymbol/body_tokens ONLY captures function/class/method bodies -- a bare
   module-level statement's tokens are invisible to both build_call_graph and
   T-0422's build_reference_graph, so a symbol wired ONLY via a top-level
   registry looks identical to genuinely dead code.
2. A smaller remainder: pytest fixtures referenced by PARAMETER NAME across
   sibling test files (never a call token or bare mention in their own file,
   e.g. `_repo_root` in tests/unit/strata/test_litmus_*.py), and what look like
   pydantic @field_validator/@model_validator methods invoked by the framework,
   never by name in tracked source (e.g. HostOwns._validate_mode,
   PolicyDecl._split_meta_rules) -- RawSymbol carries no decorator information
   to detect the latter structurally today.

Recommended follow-up direction (either, or both):
- Extend frob.lang's extraction contract with a synthetic "module scope"
  RawSymbol (or a raw top-level-statement token bucket) per file, so
  build_reference_graph can see a bare identifier mentioned in a top-level
  dict/tuple/list literal -- this alone would likely resolve the ~40-count
  class outright.
- Give RawSymbol decorator information (at least the presence of unknown
  decorators) so `_is_dunder`/`_is_test_symbol`-style exemptions can add a
  "decorated, assume framework-dispatched" rule, closing the validator-method
  class without a manual frob:waive per-symbol.

Until then: do NOT mass-waive the 51 findings blind (most are provably NOT
dead, per the manual cross-file/package grep in T-0422's Done report) --
triage each individually once the substrate gap above is closed, or waive
one at a time with a symbol-specific verified reason as they are touched by
other work.