---
id: T-4275
title: ty pre-land baseline resolution fails the same way ruff's did on Windows (T-4257
  sibling)
state: done
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land_ty_diff_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'T-4275: regression test for the ty resolve_root/empty-stdout fix lives
    in the existing land-finish test module (co-located with the sibling ruff/ty pre-land
    tests), matching where T-4257''s own tests would have gone'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'T-4275: relocating the new regression tests to the dedicated tests/test_ticket_land_ty_diff_attribution.py
    module instead avoids an unrelated SCOPE002 cascade from this large file''s own
    pre-existing cross-references'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_ticket_land_ty_diff_attribution.py
  reason: 'T-4275: regression tests for the ty resolve_root/empty-stdout fix belong
    in this repo''s existing dedicated ty-diff-attribution test module (already separated
    from the giant test_ticket_work_and_land_finish.py specifically to avoid unrelated
    cross-file coupling, per that module''s own docstring)'
  actor: logan
  at: '2026-09-08'
evidence:
- tests/test_ticket_land_ty_diff_attribution.py::TestTyCheckFilesResolveRoot::test_resolve_root_finds_ty_when_cwd_has_no_pyproject
- tests/test_ticket_land_ty_diff_attribution.py::TestTyCheckFilesResolveRoot::test_spawn_failure_reports_none_not_a_fabricated_clean_result
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while fixing T-4257's ruff land-diff-attribution failure on Windows: _ty_check_files/_ty_baseline_diagnostic_identities has the IDENTICAL shape -- it resolves ty via project_tool_argv(snapshot, ...) where snapshot is a detached git-worktree baseline checkout with no .venv of its own (uv run --project falls back to bare-PATH resolution outside any project). T-4257 fixed the ruff call site by adding a resolve_root parameter so the baseline pass resolves the tool from the real owning worktree instead of the venv-less snapshot, plus a fallback to sys.executable -m <tool> when resolve_root carries no pyproject.toml at all. The ty call site was left untouched (out of T-4257 declared scope) but almost certainly has the same latent silent-pass gap on any host (Windows CI, or any machine lacking an ambient global ty) where uv run --project a venv-less worktree cannot resolve ty: a spawn failure would currently come back as a ToolResult carrying a synthetic parse-failure Diagnostic rather than None, and since both current-pass and baseline-pass spawns fail identically, their synthetic diagnostics compare as pre-existing and the land refusal this gate exists to produce is silently swallowed. Port T-4257's two fixes (resolve_root split, and empty-stdout-is-not-a-parse-failure guard) to the ty call site.