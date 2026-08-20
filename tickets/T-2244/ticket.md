---
id: T-2244
title: Repoint trivial Makefile aliases (format/lint/typecheck/test*) at existing
  frob quality/fmt subcommands
state: in-progress
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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
attachments:
- path: T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md
  caption: 'T-2244 audit: safe-to-repoint split (test:/typecheck: safe now; lint:
    blocked by newly-found T-2387, not T-2359; format:/lint-fix: blocked by both;
    test-fast: stays raw)'
  sha256: b0ec580fcb0e0e4a77cbea888ba619fa74df8fb5884627ec35ce10a09ae47d2d
acceptance:
- text: 'GIVEN the Makefile WHEN read THEN format:/lint:/lint-fix:/typecheck: recipes
    call ''uv run frob format''/''uv run frob check --only ...'' instead of raw ruff/ty
    invocations'
  evidence: []
- text: 'GIVEN the Makefile WHEN read THEN test:/test-unit:/test-integration:/test-system:
    recipes call ''uv run frob test'' with T-2319''s directory-scoped path selection;
    test-fast: stays on raw pytest --testmon (disclosed no-frob-equivalent gap)'
  evidence: []
- text: GIVEN a deliberately introduced ruff violation or a deliberately broken test
    fixture THEN the repointed targets still fail with a nonzero exit -- no strictness
    regression from the swap
  evidence: []
acceptance_amendments:
- op: replace
  index: 0
  old_text: 'GIVEN the Makefile WHEN read THEN format:/lint:/lint-fix:/typecheck:
    recipes call ''uv run frob fmt'' / ''uv run frob quality check'' instead of raw
    ruff/ty invocations'
  new_text: 'GIVEN the Makefile WHEN read THEN format:/lint:/lint-fix:/typecheck:
    recipes call ''uv run frob format''/''uv run frob check --only ...'' instead of
    raw ruff/ty invocations'
  reason: 'premise correction: frob fmt is directive-comment canonicalization not
    ruff, and frob quality check bundles ruff-check+ruff-format inseparably with no
    write mode -- T-2251 built frob format and frob check''s existing --only/--skip-ruff-format
    stage selection is the real replacement, per this ticket''s own 2026-08-16/2026-08-18
    Failure log entries'
  actor: logan
  at: '2026-08-19'
- op: replace
  index: 1
  old_text: 'GIVEN the Makefile WHEN read THEN test:/test-fast:/test-unit:/test-integration:/test-system:
    recipes call ''uv run frob quality test'' (with the matching path/flags) instead
    of raw pytest invocations'
  new_text: 'GIVEN the Makefile WHEN read THEN test:/test-unit:/test-integration:/test-system:
    recipes call ''uv run frob test'' with T-2319''s directory-scoped path selection;
    test-fast: stays on raw pytest --testmon (disclosed no-frob-equivalent gap)'
  reason: 'premise correction: frob quality test has no directory-scoped selection
    at ticket-file time -- T-2319 landed frob test PATH''s subset semantics since,
    which is the real replacement'
  actor: logan
  at: '2026-08-19'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
format/lint/lint-fix/typecheck/test/test-fast/test-unit/test-integration/test-system are each a 1-2 line Makefile recipe calling ruff/ty/pytest directly (Makefile lines ~17-20, 530-565). frob already has first-class equivalents for every one of these ('uv run frob fmt' [--check], 'uv run frob quality check' [ruff+ty+cycle/dup/arch/bind/exports], 'uv run frob quality test' [touched-set or --all]) -- confirmed via 'uv run frob fmt --help' and 'uv run frob quality --help' today. This leaf requires NO new src/frob/** code, only Makefile edits plus a parity check per target (does frob quality test --all -n auto match today's pytest -n auto invocation's selection and exit-code semantics; does frob quality check's ruff+ty bundle a superset of today's separate lint/typecheck targets, and if so keep lint:/typecheck: as filtered views rather than silently changing what each target reports). This is the cheapest, lowest-risk leaf in the T-1382 series -- schedule it early. Does NOT include test-fast: 's --testmon flag, which has no frob quality test equivalent today; if none exists, keep test-fast: on raw pytest --testmon and disclose that gap explicitly rather than silently dropping the optimization.

## Failure log
- 2026-08-16 attempt 1: premise broken: frob fmt is directive-canonicalization not ruff format; frob quality check bundles ruff-check+ruff-format inseparably (repo has ~120 pre-existing ruff-format diffs) and has no lint-fix-equivalent write mode; frob quality test has no directory-scoped selection for test-unit/integration/system -- see T-2252
- 2026-08-18 attempt 2: Audit (not an attempt to close): 2/9 targets (test:, typecheck:) verified safe to repoint TODAY, no blocker. 3/9 (test-unit/integration/system, T-2319 landed) likely safe pending one timed parity run. lint: is blocked by a NEWLY FOUND regression (T-2387, filed: T-2320's split ruff flags + --fix-ruff are silently dropped by _BOOL_FLAGS, same class as T-0749; a pre-existing detector test for this is currently red on main) -- NOT primarily by T-2359. format:/lint-fix: need both T-2387 and T-2359. test-fast: stays on raw pytest --testmon, no frob equivalent exists, disclosed gap not a blocker. Full detail in attachment 01.
