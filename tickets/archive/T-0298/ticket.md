---
id: T-0298
title: 'COV003: resolve file-level and directory-level evidence (any collected test
  under the path)'
state: done
kind: feature
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/testing/**
- docs/modules/gates.md
- tickets.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0298 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_for_file_level_evidence
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_for_directory_level_evidence
- tests/test_gates.py::TestCoverageGate::test_cov003_rejects_empty_directory_level_evidence
- tests/test_gates.py::TestCoverageGate::test_cov003_prefers_node_level_over_path_level
designated_repro_test: null
acceptance:
- text: given ticket evidence naming a whole test FILE (tests/test_vet.py) or a DIRECTORY
    (tests/unit/deploy), when COV003 resolves it, then it resolves iff the collected
    manifest contains at least one node under that path -- not an error
  evidence: []
- text: given evidence that resolves to no collected test at any granularity (typo,
    deleted file), then COV003 still errors (the real failure is preserved)
  evidence: []
threat: null
component: null
---
Root cause of a 25-error main-red incident 2026-07-19: both arch-burndown agents recorded file-level evidence (tests/test_vet.py, tests/unit/deploy) and one embedded a kind="unit" attr into the id, none of which resolve because COV003 only matches node-level file::Class::method against the collected manifest. For a refactor touching ~20 files, "this whole test file passes" is a reasonable and natural evidence granularity; forcing one node-id per file is what led both agents (and me at close) to record unresolvable ids. Make file- and directory-level evidence first-class: resolve iff >=1 collected node lives under the path. Complements T-0293 (reject/normalize a genuinely-unresolvable id at RECORD time) and T-0292 (fix the bogus "frob test --collect" hint) -- together these make COV003 both lenient where it should be and strict where it must be. Until this lands, evidence MUST be node-level file::Class::method.