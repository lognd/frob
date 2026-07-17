---
id: T-0028
title: 'frob check red at HEAD: 16 orphan docs (DOC001) and ruff-format drift in 9
  files'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- docs/**
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
- tests/system/test_cli_check.py::TestFrobTomlCheckDefaults::test_check_skip_from_frob_toml
attachments: []
---
found while working T-0021: uv run frob check exits 1 on a clean HEAD checkout (verified in a detached worktree of 369cbd2): 17 gate errors (16x DOC001 orphan docs -- agentic-workflow/check/cycle/dup/exports/fuzz/gitlog/lang/map/outline/parse/quickstart/rework/scaffold/vet/xref -- linked from nowhere) plus ruff-format would reformat 9 committed files (src/frob/graph/__init__.py, tests/system/test_cli_exports.py, tests/system/test_cli_vet.py, tests/test_gates.py, tests/test_prework_parity.py, tests/test_testing.py, tests/test_vet.py, others). This makes the commit gate (frob check exit 0) unattainable for every in-scope ticket until cleared. Either link the docs from docs/index.md / add frob:describes anchors, and run ruff format on the drifted files.

## Done report

frob check exits 0 at HEAD again: doclink crawler now counts backtick
path references (terminal-first index style), docs/exports.md linked in
the index, --only validates stage names (unknown -> loud config error,
never a vacuous PASS) and accepts individual gate names by mapping them
onto the gates stage with sub-selection.
