---
id: T-0362
title: 'exports: export-or-demote policy per package (Error classes etc.)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**/__init__.py
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_exports.py::TestExportsPackage::test_basic_public_symbols
- tests/unit/test_exports.py::TestExportsPackage::test_private_excluded_by_default
- tests/unit/test_exports.py::TestExportsPackage::test_private_included_with_flag
- tests/unit/test_exports.py::TestExportsPackage::test_exclude_module
- tests/unit/test_exports.py::TestExportsPackage::test_not_a_directory
- tests/unit/test_exports.py::TestExportsPackage::test_no_source_files
- tests/unit/test_exports.py::TestExportsPackage::test_as_text_output
- tests/unit/test_exports.py::TestExportsPackage::test_classes_included
designated_repro_test: null
threat: null
component: null
---
T-0204 family 4: frob-exports reports src packages with public symbols (esp. Error classes: GitError, DecisionError, LockError, ScaffoldError, style_fail) not exported from __init__.py. Per-package decision required: export it, or demote the symbol to private (leading underscore / narrow scope) -- NO blanket waiver. Also assess whether the exports gate should exempt tests/ packages (test classes/functions flagged as unexported is likely mis-scoped) and file that assessment as part of this ticket's disposition. Acceptance: every reported symbol across every src package is exported or demoted with rationale; tests/ exemption question explicitly resolved (fixed or waived-with-reason); honest summary line.