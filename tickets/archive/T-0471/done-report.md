## Done report

Changed:
- src/frob/excludes.py::walk_pruned (new) -- os.walk generator, prunes
  dirnames in place via `_should_prune_dir` before descending.
- src/frob/excludes.py::iter_files (new) -- the one shared entry point;
  `git ls-files` fast path (tracked files only) when root looks like a git
  work tree, `walk_pruned` fallback otherwise; optional `suffix` filter.
- src/frob/gates/_walk_lint.py::walk_lint_gate (new module) -- WALK001,
  AST-based (matches `_pii_structural`'s precedent, not tree-sitter --
  see rationale below), self-excludes its own file and `excludes.py`.
  Flags `Path.rglob(...)` (always), `Path.glob`/`.iglob` (only `"**"`
  patterns), `os.walk(...)`, `glob.glob`/`glob.iglob` (only `"**"`
  patterns), dotted or bare-imported. An import-binding pass
  (`_collect_import_bindings`) proves a bare `walk(...)`/`glob(...)` call
  actually came from `from os import walk` / `from glob import ...` before
  flagging it -- catches the real false positive dogfooding found: a
  local `def walk(node): ...` tree-sitter-node walker in
  `frob.vet._capability` is NOT a filesystem traversal.
- src/frob/gates/__init__.py -- wired WALK001 into `_KNOWN_GATE_RULES`,
  `walk_lint` into `_ALL_GATES`/`_CANONICAL_GATE_ORDER` (set-equality
  holds, T-0438 invariant), and the process-pool job table
  (`walk_lint_gate(st.repo_root)`, whole-repo like `refs`/`registry`).
- src/frob/arch/__init__.py::_collect_files -- migrated off
  `root.rglob("*")` onto `iter_files`; dropped the now-redundant
  `_is_skip_dir` local wrapper.
- src/frob/xref/__init__.py::_collect_source_files -- migrated off
  `root.rglob("*")` onto `iter_files`.
- src/frob/vet/_closedworld.py::walk_python_imports, `_source_hash` --
  migrated onto `iter_files`.
- src/frob/vet/_scan.py::_artifact_hash -- migrated onto `iter_files`.
- src/frob/vet/_ecosystem.py::_pickle_violation -- migrated onto
  `iter_files`.
- src/frob/vet/_capability.py::_aggregate_capabilities,
  `_aggregate_fingerprints` -- migrated the per-extension `rglob(f"*{ext}")`
  loop onto `iter_files(source_dir, suffix=ext)`.
- src/frob/vet/_obfuscation.py::_collect_dir_signals -- migrated onto
  `iter_files`.
- docs/modules/app.md, docs/modules/gates.md -- documented `walk_pruned`/
  `iter_files` and the new WALK001 gate section
  (#walk001-unpruned-traversal-t-0471).

Design deviation (disclosed): the ticket suggested tree-sitter for
detection. `gates/` has no existing tree-sitter-query precedent to follow
(checked `_refs.py`/`_pii_structural.py`/`__init__.py` -- all regex or
Python `ast`); `_pii_structural.py` (T-0207) is the closest analog and
uses `ast.parse` for exactly this reason (a real `ast.Call` match, not a
lexical scan). WALK001 follows that precedent instead -- functionally
equivalent for this repo's pure-Python scope, and it is what caught and
let me fix the `walk()`-local-function false positive before landing.

Scope note: `src/frob/check/_python.py`'s three sites
(`_build_import_graph:131`, `_has_bind_markers:691`, `_run_exports:783`)
were named in the ticket body but are NOT covered by the ticket's own
declared `scope` (no `src/frob/check/` glob). A migration was drafted,
verified working, then reverted after SCOPE001 fired in `frob check
--ticket T-0471`. Not Filed as T-draft-b4a0b4be (never refiled) ("WALK-lint migration:
check/_python.py rglob sites") with the investigated diff shape noted in
its body; not force-landed here per the scope-discipline rule.
`src/frob/tickets/_repo_files` (the original T-0453 motivating site) is
explicitly out of scope per this ticket's own text (owned by T-0453/T-0458)
and untouched.

Evidence: 17 ids (see `evidence:` above), all recorded via `frob ticket
evidence T-0471 <id>...` (which re-runs each id and only accepts a
passing result) -- covers `walk_pruned`/`iter_files` pruning behavior,
WALK001 firing on rglob/glob/os.walk in dotted, bare-imported, and
false-positive-guarded forms, the shared-helper-call silence case, self-
exclusion, and the arch/xref no-longer-walks-a-nested-worktree regression
tests. Additionally ran (not bound as ticket evidence, but observed
passing): the full pre-existing `tests/unit/test_arch.py`,
`tests/test_arch_gate.py`, `tests/system/test_cli_arch.py`,
`tests/unit/test_xref.py`, `tests/system/test_cli_xref.py`,
`tests/test_vet.py`, `tests/test_vet_containment.py`,
`tests/system/test_cli_vet.py`, `tests/unit/cve/test_vet_match.py`
suites (292 tests, all pass) to confirm the arch/xref/vet migrations
preserve the intended file set. `uv run frob test --base main` (touched-
set selection) also passed (exit 0).

Not Filed: T-draft-b4a0b4be (never refiled) (check/_python.py migration, out of ticket scope).

Gates: `uv run frob check --ticket T-0471` -- SCOPE001=0, PRE001=0 (after
re-sweeping post the check/_python.py revert and post merging main).
Remaining errors on that run (`ty` on `tests/unit/strata/test_threat.py`,
`DRIFT002` on `tests/test_tickets_evidence_cli.py`, `REL001` public-API-
bump) are pre-existing/unrelated -- verified via `git diff main --stat --
<file>` showing no diff for the ty/DRIFT002 files, and REL001 is the
expected, honest consequence of `iter_files`/`walk_pruned`/`walk_lint_gate`
being new public API (version bump is a land-time/coordinator action per
the agent playbook, not mid-ticket). `git diff main --diff-filter=D
--stat` is empty (deletion-filter land rule, re-verified after merging
main forward -- main advanced 2 commits, T-0453, during this ticket;
merged cleanly, ledger auto-spliced via the merge driver). ruff-check and
ruff-format are clean on every touched file. WALK001 self-verified: fires
on a real `root.rglob("*")` fixture and on 36 pre-existing raw-traversal
sites elsewhere in `src/frob/` (WARN, not blocking) while `arch/__init__.py`
and `xref/__init__.py` no longer appear in its findings.
