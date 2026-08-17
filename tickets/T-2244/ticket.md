---
id: T-2244
title: Repoint trivial Makefile aliases (format/lint/typecheck/test*) at existing
  frob quality/fmt subcommands
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: low
blocked_by:
- T-2252
parent: T-1382
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'GIVEN the Makefile WHEN read THEN format:/lint:/lint-fix:/typecheck: recipes
    call ''uv run frob fmt'' / ''uv run frob quality check'' instead of raw ruff/ty
    invocations'
  evidence: []
- text: 'GIVEN the Makefile WHEN read THEN test:/test-fast:/test-unit:/test-integration:/test-system:
    recipes call ''uv run frob quality test'' (with the matching path/flags) instead
    of raw pytest invocations'
  evidence: []
- text: GIVEN a deliberately introduced ruff violation or a deliberately broken test
    fixture THEN the repointed targets still fail with a nonzero exit -- no strictness
    regression from the swap
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
format/lint/lint-fix/typecheck/test/test-fast/test-unit/test-integration/test-system are each a 1-2 line Makefile recipe calling ruff/ty/pytest directly (Makefile lines ~17-20, 530-565). frob already has first-class equivalents for every one of these ('uv run frob fmt' [--check], 'uv run frob quality check' [ruff+ty+cycle/dup/arch/bind/exports], 'uv run frob quality test' [touched-set or --all]) -- confirmed via 'uv run frob fmt --help' and 'uv run frob quality --help' today. This leaf requires NO new src/frob/** code, only Makefile edits plus a parity check per target (does frob quality test --all -n auto match today's pytest -n auto invocation's selection and exit-code semantics; does frob quality check's ruff+ty bundle a superset of today's separate lint/typecheck targets, and if so keep lint:/typecheck: as filtered views rather than silently changing what each target reports). This is the cheapest, lowest-risk leaf in the T-1382 series -- schedule it early. Does NOT include test-fast: 's --testmon flag, which has no frob quality test equivalent today; if none exists, keep test-fast: on raw pytest --testmon and disclose that gap explicitly rather than silently dropping the optimization.

## Failure log
- 2026-08-16 attempt 1: premise broken: frob fmt is directive-canonicalization not ruff format; frob quality check bundles ruff-check+ruff-format inseparably (repo has ~120 pre-existing ruff-format diffs) and has no lint-fix-equivalent write mode; frob quality test has no directory-scoped selection for test-unit/integration/system -- see T-2252
