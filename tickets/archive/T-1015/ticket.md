---
id: T-1015
title: 'DOC006 doc-pointer burn-down: resolve or disposition all findings, then decide
  promotion'
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged
- tests/test_docptr_gate.py::TestDoc006FilePath::test_real_path_passes
- tests/test_docptr_gate.py::TestDoc006FilePath::test_unrecognized_prose_not_flagged
- tests/test_docptr_gate.py::TestDoc006FilePath::test_dot_frob_runtime_path_not_flagged
- tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged
- tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
- tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_subcommand_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_nonexistent_flag_flagged
- tests/test_docptr_gate.py::TestDoc006Cli::test_real_command_passes
- tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged
- tests/test_docptr_gate.py::TestDoc006Config::test_real_section_passes
- tests/test_docptr_gate.py::TestDoc006Symbol::test_nonexistent_symbol_flagged
- tests/test_docptr_gate.py::TestDoc006Symbol::test_real_symbol_passes
- tests/test_docptr_gate.py::TestDoc006Symbol::test_module_dunder_init_and_all_pass
- tests/test_docptr_gate.py::TestDoc006Symbol::test_class_attribute_chain_not_flagged
- tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses
- tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_double_separator_target_flagged
- tests/test_docptr_gate.py::TestDoc006TestsTargetShape::test_single_separator_target_not_flagged
designated_repro_test: null
threat: null
component: null
---
DOC006 (docblocks gate, WARN) is turned on repo-wide with roughly 700
findings at turn-on per T-0437. This ticket burns the bucket down:

1. Measure current DOC006 findings (chunked frob check --json, per
   agent-playbook.md section 3b -- never a bare frob check).
2. Cluster findings by pointer-kind (file/path, cli invocation, config
   reference, code symbol, doc-anchor link, frob:tests shape) crossed
   with doc file, to find the dominant clusters.
3. Expect two kinds of cluster:
   - genuinely-stale doc pointers (paths/symbols renamed by prior
     refactors) -- fixable mechanically by updating the doc prose to the
     current path/symbol.
   - matcher false-positive classes -- fix the MATCHER in
     src/frob/gates/_docptr.py, not hundreds of individual waivers,
     following the T-0882/T-0910/T-0915 precedents for fixing detection
     logic instead of mass-waiving.
4. Execute the biggest clusters directly in this ticket's scope. File
   precise child tickets only for remainders that are genuinely large
   and out of this ticket's immediate reach.
5. With the resulting count evidence, decide and record in
   docs/audits/gates-quality.md whether DOC006 should promote from WARN
   to ERROR, or stay at WARN with a stated reason.

Scope: docs/**, src/frob/gates/_docptr.py, tests/test_docptr_gate.py.
Origin: agent (frob-drive DOC006 burn-down dispatch).