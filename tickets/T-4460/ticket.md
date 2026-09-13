---
id: T-4460
title: 'CI: write the self-gate and test results to the GitHub job summary'
state: queued
kind: feature
origin: human
created: '2026-09-13'
priority: medium
parent: null
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow*.py
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User request 2026-09-12: the ubuntu self-gate step failed in CI and the run page showed no summary -- the per-gate rows and the gate-summary line only exist inside the step log (thousands of lines up), and nothing writes $GITHUB_STEP_SUMMARY. ACCEPTANCE: (1) the self-gate step (and the Test step's SUITE-RESULT lines) append a compact Markdown block to $GITHUB_STEP_SUMMARY on every leg: gate-summary counts, the FAIL gate rows, and up to N error findings with rule id + file:line, plus the failed test node ids; (2) written even when the step fails (use `if: always()` on a follow-up step that reads a saved JSON, not the failing step itself); (3) tests/test_ci_workflow*.py assert the summary step exists on all legs and runs after the self-gate with always(); (4) docs/commands/check.md mentions the summary. Sprint v0.532.0.
