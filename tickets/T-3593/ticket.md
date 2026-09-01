---
id: T-3593
title: Split tests/test_vet.py (7992 lines) into a per-gate-family package, reusing
  T-3586's recipe
state: done
kind: feature
origin: agent
created: '2026-08-31'
priority: medium
blocked_by:
- T-3586
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_vet.py
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/vet_suite/test_advisories.py::TestLifecycleScripts::test_finds_postinstall_script
- tests/vet_suite/test_capability_scan_embedded.py::TestEmbeddedCodeCapability::test_embedded_html_script_string_detected
- tests/vet_suite/test_supply_chain.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCBindingResolution::test_macro_alias_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_python_exec_and_net_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustBindingResolution::test_use_as_alias_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_direct_unaliased_call_still_detected
- tests/vet_suite/test_fingerprint.py::TestObfuscationEnsemble::test_high_entropy_string_flagged
- tests/vet_suite/test_lockfile.py::TestLockfileParsers::test_find_lockfile_uv
- tests/vet_suite/test_opaque_indirection.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation
- tests/vet_suite/test_scan_tree.py::TestScanTreeLockArg::test_scan_tree_lockfile_arg
- tests/vet_suite/test_scan_tree.py::TestVetRunnerLockArg::test_run_lockfile_arg
- tests/test_vet.py::test_parse_hook_command_scoped_npm_package
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Sibling split to T-3586 (which owns tests/test_gates.py, 21691 lines,
the FIRST split and the recipe owner). This ticket owns ONE of the five
other monofile test suites named in T-3586's MEASURED wc -l list:

    12596 tests/test_ticket_land.py
     8910 tests/unit/test_arch.py
     7992 tests/test_vet.py
     5935 tests/unit/test_coordinator_scripts.py
     5055 tests/unit/test_rapid_sweep.py

RECIPE (established by T-3586, T-3587):

1. `frob refactor split`/`move`/`move-module` needed T-3587 first
   (landed: module_to_path hardcoded src/ as the sole package root, so
   the verbs could not address any tests/** module at all -- fixed via
   a shared import_roots/root_for_path root list). Confirm the T-3587
   fix is on `main` before starting -- `uv run frob refactor split
   tests.<this-file-without-py> --symbols X --into tests.gates_suite.x`
   (or your own destination package name) should resolve without a
   "module file missing: .../src/tests/..." error.

2. Cluster this file's test classes by family (section comments/class
   names make this mechanical) into one module per family under a new
   sibling package, using `frob refactor split --skip-check-delta`
   (`frob check --delta`'s own 100s budget is exceeded by this repo's
   size regardless of diff size -- a pre-existing infra cost, not a
   split defect; verify with your own scoped `frob check` instead,
   never skip verification, just don't rely on split's internal
   check_delta post-condition).

3. AFTER each split, the re-export shim `split` leaves in the source
   module (`from DEST import (...)  # noqa: F401`) causes pytest to
   DOUBLE-COLLECT every moved test class -- pytest gathers any
   `Test*`-named object visible in a module's namespace, imported or
   locally defined, not just AST-defined-there. Remove the shim block
   after confirming (via `git diff`) every repo-local frob:tests/
   evidence reference was already rewritten by the split's own
   transaction (it always is -- that IS the transaction's job); then
   re-verify collection count with `pytest <both files>
   --collect-only -q` and confirm it matches the pre-split total
   exactly.

4. `frob refactor move` (unlike `split`, T-3122) does NOT carry
   forward imports a moved symbol's body or default-argument
   expressions need, and neither `move` nor `split` patches OTHER
   files' (including the source module's own remaining classes', or a
   freshly split-out destination module's) bare-name references to a
   symbol that moved out from under them -- only explicit `from X
   import symbol` statements get rewritten. Any shared test helper
   (`_write`, `_snapshot`, fixture-style functions, etc.) used across
   multiple families needs: (a) `frob refactor move
   tests.<file>:_helper tests.conftest:_helper` for each one,
   one at a time (its own module-import verify step will surface any
   missing carried-forward import -- add the single missing import
   line by hand, confirmed minimal); (b) a manual `from tests.conftest
   import (...)` block added to every surviving file that references
   the helper as a bare name (the source file and any split
   destination files) -- this is fixing a documented tool gap, not a
   hand-move of test logic; never author new test bodies by hand.

5. A module-level CONSTANT (e.g. a string/tuple fixture literal) used
   across families cannot be moved by `move`/`split` at all -- v1 scope
   is function/class defs only (`frob.refactor._resolve.resolve_symbol`'s
   own docstring). Relocate these by hand into tests/conftest.py (or
   this ticket's own shared module) for the same reason as (4b).

6. Preserve markers: `xdist_group`/`timeout`/T-2099's
   heavy_subprocess-by-MODULE grouping -- moving a class to a new
   module changes its T-2099 group key; note the effect on
   parallel/peak-memory behavior for any class carrying that marker.

7. Prove closure per batch: `frob check --only gates-fast --budget 300
   --ticket <this-id>` before landing, plus the moved+source files'
   own pytest run at 100% green with the exact pre-split collection
   count.

ACCEPTANCE: this file either deleted or reduced to a thin re-export
shim under 200 lines (state which and why, matching T-3586's own
precedent); zero new gate errors; collection count preserved exactly.