---
id: T-0372
title: 'arch: large-file must skip non-source data files (.json/.md ledgers/.lock/release.json)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/arch/
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestLargeFile::test_large_json_data_not_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_md_ledger_not_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_py_src_still_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_src_file_still_flagged
- tests/unit/test_arch.py::TestLargeFile::test_large_test_file_not_flagged
designated_repro_test: null
threat: null
component: null
---
frob-arch large-file flags ~68 files including NON-SOURCE data: .frob-release.json (946 lines, generated API stamp), tickets-archive.md (21214 lines, the ledger archive), likely uv.lock and docs. arch's size heuristic is about CODE module cohesion; a generated JSON stamp or a ticket ledger is not an over-large module. Extend T-0368's data-file exemption: _check_large_file should only apply to files arch actually parses as SOURCE (has a tree-sitter grammar via _has_tree_sitter_grammar / frob.lang.tree_sitter_extensions), OR explicitly skip known data/generated extensions (.json,.md,.lock,.toml,.txt,.cfg) and generated artifacts (.frob-release.json). Do NOT exempt real source (.py/.rs/.ts/.c/.cpp). Then the residual large-file findings are only genuine large SOURCE modules (a separate refactor decision). Add tests: a 1000-line .json -> not flagged; a 1000-line .py -> flagged. Acceptance: large-file fires only on source files; honest count.