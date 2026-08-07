## Done report

Fix: added a shared `_prune_dirnames` helper in
`src/frob/testing/_collect.py` (used by both `_walk_test_files` and
`_find_crates`) that drops a child directory name if it is either in
the built-in skip set (`frob.excludes.is_skipped_dir`) OR matches
`[graph].exclude` (`frob.excludes.load_exclude_globs`/`is_excluded`),
replacing the old local `_EXCLUDED_DIRS` frozenset entirely. Applied
the same per-file exclude check to `bind_code` (`_code_binding.py`)
and `_sorted_capability_files` (`_selfconform.py`), both of which
already imported `is_skipped_dir` from `frob.excludes` but never
`load_exclude_globs`/`is_excluded`.

Tests added: `TestFindCrates::test_find_crates_honors_graph_exclude`
and `::test_walk_test_files_honors_graph_exclude`
(`tests/test_testing.py`, a stale `.claude/worktrees/agent-x/**`
crate/test-file fixture with a matching `[graph].exclude` glob must be
pruned before its own `Cargo.toml`/test file is ever inspected);
`TestBindCode::test_graph_exclude_dir_is_never_bound_even_when_glob_matches`
(`tests/unit/strata/test_code_binding.py`) and
`TestNonPythonLanguageWiring::test_sorted_capability_files_honors_graph_exclude`
(`tests/unit/strata/test_selfconform.py`), both reproducing the exact
graphite FROBLEMS.md shape (bundled build dir under a `code=`-globbed
directory) directly against the file-walk function, not just the
end-to-end gate.

All 4 new tests pass; full repo suite `uv run pytest tests/ -q -n
auto` green after the change (confirmed twice, once before and once
after a `make core` native-extension rebuild this session needed
anyway for an unrelated stale-`.venv` reason).

NOTE (incident, not part of the fix): this repo is being worked
concurrently by other agents/sessions committing directly to this
same `main` checkout (HEAD advanced by 9 unrelated commits --
T-0217/T-0193/T-0256/T-0273-adjacent work -- while this ticket's edits
were in progress, uninvolved with this ticket), and at one point ALL
of this ticket's uncommitted working-tree edits (across
`_collect.py`, `_code_binding.py`, `_selfconform.py`, and three test
files) were silently wiped back to a clean `HEAD` between tool calls,
with no error surfaced. Redone from scratch this round and committed
immediately after landing to minimize further exposure. Flagging this
loudly per the dispatch's report-design-gaps instruction: dispatching
multiple agents onto the SAME non-worktree checkout is unsafe for
uncommitted work; a git worktree per agent (as this repo's own
playbook already prescribes for OTHER dispatches) would have
prevented this.
