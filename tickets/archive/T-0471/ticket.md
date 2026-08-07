---
id: T-0471
title: 'WALK-lint: gate against unpruned filesystem traversals (rglob/glob**/os.walk
  that walk a root without frob.excludes pruning -- descend into .git/.venv/node_modules/.claude/worktrees)
  + provide a shared prune-aware walk helper + migrate the offending sites (arch/xref
  root.rglob, vet scanners, T-0453 _repo_files)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/excludes.py
- src/frob/gates/
- src/frob/arch/
- src/frob/xref/
- src/frob/vet/
- docs/
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_walk_lint_gate.py::TestRglob::test_raw_rglob_fires
- tests/test_walk_lint_gate.py::TestRglob::test_gate_fires_on_new_raw_root_rglob
- tests/test_walk_lint_gate.py::TestConditionalGlob::test_recursive_glob_pattern_fires
- tests/test_walk_lint_gate.py::TestConditionalGlob::test_non_recursive_glob_pattern_is_silent
- tests/test_walk_lint_gate.py::TestOsWalk::test_dotted_os_walk_fires
- tests/test_walk_lint_gate.py::TestOsWalk::test_bare_imported_walk_fires
- tests/test_walk_lint_gate.py::TestOsWalk::test_local_function_named_walk_is_not_flagged
- tests/test_walk_lint_gate.py::TestOsWalk::test_aliased_os_walk_import_fires
- tests/test_walk_lint_gate.py::TestHelper::test_helper_call_is_silent
- tests/test_walk_lint_gate.py::TestHelper::test_walk_pruned_call_is_silent
- tests/test_walk_lint_gate.py::TestSelfMatchExclusion::test_own_files_not_scanned
- tests/test_walk_migration.py::test_arch_does_not_walk_nested_worktree
- tests/test_walk_migration.py::test_xref_does_not_walk_nested_worktree
- tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git
- tests/test_excludes.py::test_iter_files_falls_back_to_walk_pruned_outside_git
- tests/test_excludes.py::test_iter_files_suffix_filter
- tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: lint for this class so it cannot recur. T-0453's
`_repo_files` did `root.rglob("*")` -- walking the ENTIRE tree including .git,
.venv, __pycache__, and the ~129 stale worktrees under .claude/worktrees/ --
making `frob ticket doable` take minutes. frob ALREADY has the shared prune
machinery (src/frob/excludes.py: _should_prune_dir / is_always_pruned_dir /
the built-in skip set + frob.toml globs, established by T-0335 for os.walk
sites), but many raw traversals bypass it. Turn the mistake into a static
check.

Offending sites found (raw recursive walk, NOT routed through excludes'
pruning -- these descend into heavy/irrelevant dirs):
- src/frob/arch/__init__.py:59  `root.rglob("*")`  (whole repo)
- src/frob/xref/__init__.py:140 `root.rglob("*")`  (whole repo)
- src/frob/vet/_capability.py:2642/2695, _closedworld.py:82/160,
  _ecosystem.py:79, _obfuscation.py:279, _scan.py:58 -- rglob a dependency
  source_dir (can descend into a dep's .venv/node_modules)
- src/frob/check/_python.py:131/689/780 -- rglob scan_root
- (src/frob/tickets/_repo_files -- the T-0453 instance, being fixed to
  git ls-files there)
(scoped small-dir walks like design_dir.rglob("*.strata") are fine.)

Design (three parts):
1. PROVIDE one shared prune-aware walk primitive in frob.excludes, e.g.
   `iter_files(root, *, suffix=None)` / `walk_pruned(root)` that wraps os.walk
   and prunes dirnames in place via _should_prune_dir BEFORE descending (never
   yields a path under .git/.venv/node_modules/.claude/build/dist/target/
   __pycache__/*.egg-info). Prefer `git ls-files` fast-path when root is a git
   work tree (tracked files only) with the os.walk-prune fallback otherwise.
2. GATE (new rule, e.g. WALK001 / PERF005): flag any `Path.rglob(...)`,
   `Path.glob("**"...)`, `os.walk(...)`, `glob.glob("**"...)`, `glob.iglob(
   "**"...)` in src/frob/ that is NOT the shared helper and does NOT visibly
   prune. Detect via tree-sitter (call-expression on rglob/glob/walk with a
   recursive pattern). Waivable per-line for a genuinely-bounded small-dir
   walk with a reason. Message names the remedy: "route through
   frob.excludes.iter_files / walk_pruned so it prunes .git/.venv/worktrees".
3. MIGRATE the offending sites above to the helper (whole-repo walks first:
   arch, xref; then the vet scanners; check/_python). Each migration keeps
   behavior (same file set minus the correctly-pruned junk).

Acceptance: a new raw `root.rglob("*")` added anywhere in src/frob/ fails
frob check (WALK gate); the helper prunes the standard heavy dirs (test: a
tree with a .venv/ and .git/ inside is not descended); arch/xref/vet/check
walks go through the helper; `frob ticket doable` (once T-0453 lands its
git-ls-files fix) and `frob arch`/`frob xref` no longer walk .claude/
worktrees. Relates T-0335 (os.walk prune), T-0245 (mount-aware perf), and
the T-0453 _repo_files perf fix that motivated this.