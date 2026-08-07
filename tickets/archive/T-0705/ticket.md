---
id: T-0705
title: 'gates: git-less target dirs hard-error 4 gates (git ls-files exit 128) --
  ~12 system-test failures'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/system/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: documenting the git-less-target contract decision the ticket explicitly
    asks for
  actor: logan
  at: '2026-07-22'
evidence:
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
designated_repro_test: null
acceptance:
- text: GIVEN the ~12 currently-failing system tests WHEN the suite runs THEN they
    pass AND a git-less target produces a consistent, documented behavior across all
    gates
  evidence: []
threat: null
component: null
---
CI triage 2026-07-22 (the bulk of the cancelled 6h run's F markers, reproduced on current main): secrets_gate, pii_structural_gate, render_lint_gate, walk_lint_gate emit ERROR 'git ls-files exited 128' when frob check targets a directory that is not a git repository (the system tests' /tmp fixture repos without git init), failing ~12 tests across test_cli_check.py, test_cli_perf.py. Other gates only WARN on the same condition (ref_gate, doc004). Decide the correct contract (docs/modules/gates.md): EITHER gates degrade gracefully on git-less targets (warn + fall back to filesystem walk, matching ref_gate/doc004's posture) OR frob check declares git a hard requirement and the FIXTURES gain git init. Pick ONE, apply consistently across all four gates or all fixtures, and make the currently-failing tests pass without weakening what the gates check in real repos.