---
id: T-1572
title: 'frob coverage: add --base override, thread through make coverage-fast BASE='
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/coverage_runner.py
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/coverage_runner.py
  reason: 'identify actual implementation surface before failing: --base wiring needs
    both this runner/config AND _add_coverage_parser in src/frob/_cli_parsers/_misc.py,
    which is explicitly off-limits per dispatch'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: 'identify actual implementation surface before failing: --base wiring needs
    both this runner/config AND _add_coverage_parser in src/frob/_cli_parsers/_misc.py,
    which is explicitly off-limits per dispatch'
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
threat: null
component: null
---
Refiled from worktree draft T-draft-a385ed9f (T-1526 follow-up; drafts cannot be cited by reports that must survive a land preview). make coverage-fast BASE=<ref> was honored by the old shell recipe but frob coverage currently hardcodes the touched-set base; add a --base flag and pass BASE through the Makefile wrapper.

## Failure log
- 2026-08-08 attempt 1: requires editing src/frob/_cli_parsers/_misc.py (_add_coverage_parser) to wire a --base CLI flag through to coverage_runner.run; that file is on the dispatch's explicit off-limits list held by another agent, so this cannot be implemented within my declared scope/constraints. Runner-side work (coverage_runner.py/config.py) is a small, mechanical addition once the flag exists; only the CLI parser edit is blocked.
