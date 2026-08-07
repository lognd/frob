---
id: T-1104
title: 'docs: document T-1102 single-file-mode parity + LARGE001 in docs/modules/arch.md
  (analyze_project anchors)'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/arch.md
- src/frob/arch/__init__.py
- tests/unit/test_memo.py
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_memo.py
  reason: 'docs-kind ticket: bind evidence test files in scope before landing (playbook
    recurring-refusal note)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_arch_gate.py
  reason: 'docs-kind ticket: bind evidence test files in scope before landing (playbook
    recurring-refusal note)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
- tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk
designated_repro_test: null
acceptance:
- text: given docs/modules/arch.md, when the section lands, then analyze_project's
    single-file behavior and the LARGE001 channel are documented at the anchors its
    frob:doc directives cite, and the AFFECT001 waiver T-1102 placed at the touched
    symbol is retired
  evidence:
  - tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk
threat: null
component: null
---
Refile of T-1102's dead draft T-1104 (post-close renumber loss). docs/modules/arch.md was outside T-1102's declared scope; this carries the doc debt plus retiring the disclosed AFFECT001 waiver.