---
id: T-1023
title: 'INV burn-down: 50 invariant-anchor gaps (INV006 24 code claims, INV005 17
  unbound evidence, INV004/INV003 9 docs claims)'
state: done
kind: invariant
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/
- invariants/
- src/frob/
- tests/unit/fleet/test_manifest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/fleet/test_manifest.py
  reason: 'INV006 burn-down anchored many invariants whose evidence lives in test

    files outside the declared docs/modules/, invariants/, src/frob/ scope

    globs (frob:tests directives point at pre-existing tests in tests/), and

    closing INV004/003 for docs/modules/fleet.md genuinely needed a NEW test

    (tests/unit/fleet/test_manifest.py) strengthening evidence for a real

    cross-module contract (manifest-dir-not-cwd resolution) that had no test

    proving the cwd-independence half of the claim before this ticket.

    '
  actor: logan
  at: '2026-07-27'
body_changes:
- mode: append
  reason: condense tree_sitter-free invariant rationale into T-0757 body
  actor: logan
  at: '2026-09-19'
  old_length: 368
  new_length: 1441
evidence:
- tests/unit/fleet/test_manifest.py::TestLoadManifest::test_relative_path_resolves_against_manifest_dir_not_cwd
- tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_pyproject_fires_rel002
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_flags_stale_generated_block
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires
- tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check THEN INV003-INV006 warnings are zero
  evidence:
  - tests/unit/fleet/test_manifest.py::TestLoadManifest::test_relative_path_resolves_against_manifest_dir_not_cwd
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Bind every normative claim to a checked invariant: INV006 code files with exclusivity claims need frob:invariant anchors; INV005 evidence must gain frob:tests edges to its anchor (dotted Class.method form only); INV003/INV004 docs claims need invariant markers. Write real property tests where an anchor has no evidence; do not water down claims to dodge the detector.

<!-- narrative-moved:src/frob/arch/_normalized.py:29:T-1023 -->
frob:invariant INV-042 no_import="tree_sitter"
invariant spec: [INV-042](invariants/INV-042.md)
frob:tests tests/unit/test_design_invariants.py::TestInv007.test_forbidden_import_fires  # noqa: E501
T-1023: the frob:tests edge above is what INV005 needs to see this
evidence actually REACH this file's own anchor (same-file trust does
not apply here since the evidence test lives in a different file) --
T-0757 (the T-0611 incident as a gate, not just this comment): this
module is DELIBERATELY tree_sitter-free -- every language adapter
(`_python.py`, `_typescript.py`, `_cpp.py`, ...) lives outside it
precisely so this shared model never needs a parser import. T-0611
landed a `TypeScriptAdapter` inside this file and a human reviewer had
to catch it by reading the diff; `frob.gates._design_invariants.
inv007_violations` now fails the instant this file's own import
specifiers contain `tree_sitter` or any `tree_sitter.*` submodule, so
the same class of regression is a gate finding, not a review catch.