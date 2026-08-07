## Done report

`frob-exports` (`src/frob/check/_python.py`) is a `note`-severity, `exit_code=0`
diagnostic tool, not a gates rule -- there is no `EXPORTxxx` id and nothing to
`frob:waive`; its check is a literal `sym not in init_src` substring test
(`_missing_exports`). Findings before this ticket: 147 src symbols (+1125
tests/) flagged; after: 74 src (0 tests/).

Per-symbol decisions (grouped; every symbol was checked individually via
grep for real cross-package/cross-file imports before deciding, not
pattern-matched):

EXPORTED (73 symbols, real public API -- Error classes callers catch, or
genuine cross-module/cross-package `from frob.x import y` usage):
- `frob/__init__.py` (new file, was empty): `frob.gitio`'s `GitError`,
  `Diff`, `Hunk`, `ProcResult`, `current_branch`, `repo_root`, `run_argv`,
  `working_diff` and `frob.excludes`'s `is_excluded`, `is_skipped_dir`,
  `load_exclude_globs` -- all imported by name from 8+ other packages.
- `frob/app/__init__.py`: `Subcommand` (documented CLI-surface enum);
  `app._style`'s 7 `style_*` helpers (shared across sys/vet/stats/ticket
  runners); all 25 `*_runner.run` functions, module-aliased
  (`ack_runner_run`, ...) since `frob.app.app` reaches every one of them by
  name via `importlib.import_module(...)` + `getattr(..., "run")` --
  genuinely the package's dispatch-table public surface, just reached
  dynamically rather than by static import.
- `frob/cycle/__init__.py` (new file, was empty): `DependencyGraph`,
  `find_cycles` -- imported by `frob.check._python` and
  `frob.app.cycle_runner`.
- `frob/graph/__init__.py`: `is_generated_source` (used by `frob.gates`),
  `CallGraph`/`build_call_graph` (used by `frob.dup._pipeline`), `closure`
  (same module's third public function, tested directly, kept with its
  siblings for API-surface consistency), `LockError`/`acknowledge`/
  `load_lock`/`write_lock` (used by `frob.gates`, `frob.serve._tools`,
  `frob.app.ack_runner`). `graph.lock` imports `resolve` back from
  `frob.graph`'s own `__init__.py`, so its import had to move to the
  bottom of the file (after `resolve` is defined) to avoid a circular
  partial-init `ImportError` -- verified by `python -c "import frob.graph"`
  before and after.
- `frob/gates/__init__.py`: `DecisionError` (ticket's named example --
  `load_decisions`'s error type; `Decision`/`DecisionStatus` were NOT
  exported, see below).
- `frob/lang/__init__.py`: `flatten_tree` (used by `frob.dup._pipeline`
  and `frob.dup._template`; its 7 `lang._common` siblings were NOT
  exported, see below).
- `frob/logging/__init__.py`: `paint`, `should_color` (used by
  `frob.check`, `frob.perf._heat`, `frob.app.vet_runner`/`stats_runner`).
- `frob/process/parsers/__init__.py`: `tool_unavailable_result` (used by
  `frob.check._python`/`_ts`) and `summarize_severity` (used by all 8
  sibling parser modules -- package-wide internal API, exported for the
  same reason `style_fail` was).
- `frob/scaffold/__init__.py` (new file, was `from __future__ import
  annotations` only): `ScaffoldError`, `list_project_types`,
  `render_project` -- all used by `frob.app.scaffold_runner`.
- `frob/serve/__init__.py`: `McpUnavailable`, `build_server`, `run_stdio`
  added via a lazy `__getattr__` (not a top-level import) -- `server.py`
  imports the optional `mcp` SDK at module scope, and the package
  docstring already promises `frob.serve` core stays importable without
  `mcp` installed; a top-level import would silently break that contract.
  Verified `import frob.serve` still succeeds and `frob.serve.McpUnavailable`
  resolves.
- `frob/tickets/__init__.py`: `clipboard_has_image` (used by
  `frob.app.ticket_runner`; `_store.parse_ticket_file`/`serialize_ticket`/
  `store_mode` were deliberately NOT added, see below -- the file already
  curates a specific subset of `_store`'s exports and always excluded
  those three).
- `frob/vet/__init__.py`: `is_self_pattern_path`, `language_for`,
  `scan_file_capabilities` (used by `frob.strata._effects`/
  `_selfconform`), `capability_matrix` (used by `frob.app.sys_runner`).

WAIVED WITH INLINE RATIONALE (2 symbols, genuine entrypoints where
re-exporting from `__init__.py` would be either meaningless or actively
harmful -- documented as a reasoned comment, not a blanket suppression,
since `frob-exports` has no formal waiver mechanism to attach to):
- `frob.__main__.main`: reached by `pyproject.toml`'s `[project.scripts]`
  entry `frob = "frob.__main__:main"`, a direct module:function path that
  bypasses `frob/__init__.py` entirely. Re-exporting it would force every
  `import frob.<anything>` in the codebase (which all trigger
  `frob/__init__.py` first) to pay for building the full CLI dispatch
  table at import time. Rationale recorded in `frob/__init__.py`'s module
  docstring.
- `frob.perf._harness.main`: invoked as a subprocess script
  (`python _harness.py <pstats-out> ...` via `runpy`, see
  `_profile.py`'s `_harness_argv`), never imported by any package.
  Rationale recorded as a comment in `frob/perf/__init__.py`.

LEFT UN-EXPORTED, DEFERRED TO T-draft-b427fa47 (never refiled) (74 symbols -- true
package-internal implementation helpers: 0-1 intra-package consumer
files, never imported outside their own package, module already
underscore-prefixed): `dup._core.*` (7), `dup._cache.close_all`,
`dup._pipeline.probe_smt_equivalence`, `gates._pii_structural.*` (3),
`gates._secrets.redact`, `gates.decisions.{Decision,DecisionStatus}`,
`gates.invariants.Criticality`, `graph.digest.{digest_body,digest_doc,
digest_sig}`, `lang._common.{collapse_ws,find_enclosing_symbol,
find_following_symbol,leading_doc_comment,leaf_tokens,span_of,
strip_comment_delims}`, `logging.filter.BelowLevelFilter`,
`logging.formatter.FrobFormatter`, `strata._ast.*` (3),
`strata._host.host_attrs`, `strata._krb.krb_attrs`, `strata._waive.*` (3),
`tickets._store.{parse_ticket_file,serialize_ticket,store_mode}`,
`vet._allow.load_vet_config`, `vet._cache.*` (2),
`vet._capability.{decode_to_exec_signal,scan_directory_capabilities,
scan_directory_fingerprints,scan_file_fingerprints,scan_file_operations}`,
`vet._capability_registry.{DangerousOperation,MatrixCell,MatrixExcuse,
unexcused_empty_cells,validate_registry_kinds}`, `vet._ecosystem.*` (3),
`vet._lifecycle.scan_lifecycle_scripts`, `vet._lockfile.*` (2),
`vet._models.HookAction`, `vet._obfuscation.*` (5), `vet._osv.*` (2),
`vet._registry.*` (2), `vet._source.*` (4), `vet._typosquat.*` (2).
Why not demoted now: renaming each to a leading underscore is safe for
its sole intra-package caller, but every one of these 74 symbols is ALSO
imported directly by name in one or more `tests/*.py` files (e.g.
`from frob.vet._typosquat import find_typosquat`) -- confirmed with a
per-symbol grep over `tests/`. This ticket's scope is
`src/frob/**/__init__.py` + `src/frob/**`; `tests/` is out of scope, and
renaming without updating those test imports would break the suite. Not Filed
as T-draft-b427fa47 (never refiled) (parent T-0204) with the exact symbol list and plan
(rename + update sole intra-package caller + update the matching test
import) rather than silently leaving the cut undocumented.

tests/ exemption (required by acceptance): resolved by FIXING the checker,
not waiving it. `frob.check._python._exports_for_package` now skips any
package directory with a `tests` path component (alongside the existing
`.hidden`/`__pycache__`/`build`/`dist` skip-list), with a docstring
explaining why: pytest `test_*`/`Test*` symbols are collected by pytest's
own discovery, never imported through a package `__init__.py`, so flagging
1125 of them as "should be exported" was a mis-scoped check for a
directory that is not a public-API package. Verified: `tests/` findings
147->0 before/after fix; `1125->0` tests/ findings total.

Changed:
- frob/__init__.py (new)
- frob/app/__init__.py
- frob/cycle/__init__.py (new)
- frob/graph/__init__.py
- frob/gates/__init__.py
- frob/lang/__init__.py
- frob/logging/__init__.py
- frob/process/parsers/__init__.py
- frob/scaffold/__init__.py (new)
- frob/serve/__init__.py
- frob/tickets/__init__.py
- frob/vet/__init__.py
- frob/perf/__init__.py (comment only, no new export)
- frob/check/_python.py (tests/ exemption fix in `_exports_for_package`)

Evidence:
- `uv run frob check --only exports`: src not-exported count 147 -> 74;
  tests/ not-exported count 1125 -> 0.
- `uv run frob check --delta`: 0 new errors (22 pre-existing warnings, 34
  pre-existing waived findings, all unrelated to this diff -- confirmed by
  reading the delta output, not the raw baseline-stale full-repo output).
- `uv run ruff check <all changed files>` clean under both `uv run ruff`
  and PATH `ruff`.
- `python -c "import frob, frob.app, frob.cycle, frob.graph, frob.gates,
  frob.lang, frob.logging, frob.process.parsers, frob.scaffold,
  frob.serve, frob.tickets, frob.vet, frob.dup"` -- succeeds (catches the
  `frob.graph`/`frob.graph.lock` circular-import regression before it
  reached tests).
- `tests/unit/test_exports.py::TestExportsPackage::test_basic_public_symbols`
- `tests/unit/test_exports.py::TestExportsPackage::test_private_excluded_by_default`
- `tests/unit/test_exports.py::TestExportsPackage::test_private_included_with_flag`
- `tests/unit/test_exports.py::TestExportsPackage::test_exclude_module`
- `tests/unit/test_exports.py::TestExportsPackage::test_not_a_directory`
- `tests/unit/test_exports.py::TestExportsPackage::test_no_source_files`
- `tests/unit/test_exports.py::TestExportsPackage::test_as_text_output`
- `tests/unit/test_exports.py::TestExportsPackage::test_classes_included`
  (all 8 collected and passing, `pytest tests/unit/test_exports.py -q`)
- Full targeted run, all passing, 0 failures: `tests/test_vet.py`,
  `tests/test_gates.py`, `tests/test_tickets.py`, `tests/test_serve.py`,
  `tests/test_graph.py`, `tests/test_graph_lock.py`, `tests/test_lang.py`,
  `tests/test_perf.py`, `tests/unit/test_app.py`,
  `tests/unit/test_app_style.py`, `tests/unit/test_app_runners.py`,
  `tests/unit/test_cycle.py`, `tests/unit/test_process.py`,
  `tests/unit/test_scaffold_project.py`, `tests/unit/test_exports.py`
  (`uv run pytest ... -q -p no:cacheprovider`, no per-test-id assertion
  beyond "existing suite still passes" since the exports change itself has
  no dedicated regression test -- see below).
- No new test was added for the `_exports_for_package` tests/-exemption
  fix itself: it is a private helper inside a `check` tool
  (`src/frob/check/_python.py`), and adding a regression test would
  require touching `tests/`, which is out of this ticket's declared
  scope. Deferred to T-draft-b427fa47 (never refiled) alongside the true-demotion work
  (which also needs `tests/` access) rather than silently expanding scope.

Not Filed: T-draft-b427fa47 (never refiled) (parent T-0204) -- demote the 74 true-internal
symbols left un-exported above; needs both `src/frob/**` and `tests/**`
scope since every one has a direct `tests/` import of the current name.

Gates: `uv run frob check --ticket T-0362` reports the `frob-exports` tool
results as `pass` (note-severity, exit_code=0, not a gate) with the
symbol counts above. No `frob:waive` needed (no waivable rule exists for
`frob-exports`); the 2 entrypoint decisions are recorded as inline
code-comment rationale instead, per-symbol, not blanket.

Post-merge update: `main` moved forward mid-ticket (T-0359/T-0363
landed concurrently, 12 commits, `git diff main --diff-filter=D` caught a
842-line test file main had that my pre-merge HEAD didn't); merged main
in, resolved the `tickets.md` ledger conflict per the splice rule (kept
both appended ticket sections, T-draft-b427fa47 (never refiled) and main's T-0366/T-0367/
T-0368, un-interleaving them), re-verified `git diff main --diff-filter=D`
is now empty, re-ran the full targeted test list plus
`tests/unit/test_app_runners_batch5.py` -- all pass. The merge surfaced
one more `frob-exports(src/frob)` finding, `frob.excludes.is_test_file`
(added by T-0359, used cross-package by `frob.arch`/`frob.testing._select`/
`frob.gates`) -- exported it in `frob/__init__.py` alongside the others,
same per-symbol reasoning as the rest of this ticket.

`uv run frob check --ticket T-0362` at final merged HEAD shows 4 gate
errors, all pre-existing/out of this ticket's scope, not introduced by
this diff:
- 2x `DRIFT002` (`tests/unit/test_arch.py` -> `src/frob/arch/__init__.py::
  _is_test_file` no longer resolves) and 1x `COV001` (`excludes.py::
  is_test_file` missing `frob:doc`): all three are `frob.excludes`/
  `frob.arch` doc-drift left by main's own concurrent T-0359 commit
  (`refactor(excludes): hoist is_test_file to single shared home`),
  confirmed present in `main`'s own `excludes.py` (has `frob:tests`, no
  `frob:doc`) independent of anything this ticket touched; T-0362's scope
  is `src/frob/**/__init__.py` + `src/frob/**` generally but the doc-anchor
  fix belongs to whoever owns the T-0359 arch/excludes refactor, not an
  exports-policy ticket -- left for that family to close out.
- 1x `REL001` (public API changed since stamped version 0.27.0): expected
  and partly caused by this ticket's own new exports (by design -- the
  point of the ticket was growing each package's public surface), but a
  version bump + `frob release stamp` is a repo-wide release-cadence
  action, not a per-ticket one; deferred to whoever next runs a release
  stamp (land time), consistent with how other T-0204-family tickets in
  this batch have not self-stamped either.
