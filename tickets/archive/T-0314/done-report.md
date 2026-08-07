## Done report

Changed:
- `src/frob/gates/__init__.py::_GateInputs` -- added a `repo_root: Path` field
  alongside `root`. `root` stays the (possibly scoped) `cfg.root`, filtering
  which files a gate scans/reports; `repo_root` is always the git/frob root,
  for directives whose target is repo-relative path text.
- `src/frob/gates/__init__.py::_repo_root_for` (new) -- resolves the repo
  root for a given `root` via `frob.gitio.repo_root`, falling back to `root`
  itself when it's not inside a git repo (never a bare Result to unwrap).
- `src/frob/gates/__init__.py::_assemble_gate_inputs` -- now computes
  `repo_root=_repo_root_for(root)` when building `_GateInputs`.
- `src/frob/gates/__init__.py::_build_jobs` -- the `"docanchor"` job now
  calls `docanchor_gate(st.repo_root, st.snapshot)` instead of
  `docanchor_gate(st.root, st.snapshot)`. This is the exact one-line fix for
  the bug: DOC002's `<file>#<anchor>` target resolution (`root / docfile`
  inside `_docanchor_check_edge`/`_doc_anchor_slugs`) now always resolves
  against the repo root, never the scoped subdir a `frob check <subdir>`
  run passed in. `check_runner.py::_dispatch_check_python` itself needed no
  change -- `root` reaching `run_check`/`run_gates` is correctly the scoped
  path for "which files are gated" (a); the bug was entirely in gate (b),
  docanchor's resolution of a repo-relative directive target, which is now
  fixed at the `_GateInputs`/`_build_jobs` layer where `st.root` vs.
  `st.repo_root` can be told apart. `docanchor_gate`'s docstring updated to
  say explicitly which root it expects.
- `src/frob/gates/__init__.py::docanchor_gate` -- docstring only (no
  signature change): documents that its `root` param must be the repo root.
- `tests/system/test_cli_check.py::TestCheckDocAnchorScopedVsUnscoped.test_scoped_docanchor_matches_unscoped`
  (new) -- the litmus: a repo-root `docs/x.md` with a `## Widget` heading,
  a `pkg/sub/mod.py` carrying `# frob:doc docs/x.md#widget`, gated once via
  `frob check <repo-root> --only docanchor` and once via
  `frob check <repo-root>/pkg/sub --only docanchor` -- asserts DOC002 absent
  and exit 0 from BOTH. Verified this reproduces the bug: stashing only the
  `src/frob/gates/__init__.py` change and re-running this test fails with
  `DOC002: frob:doc target file 'docs/x.md' does not exist` on the scoped
  run only (unscoped stays clean) -- exactly the symptom in the FROBLEM.
- `tickets.md` -- fixed T-0314's own `scope` field, found stale/malformed
  during this ticket's own SCOPE001 gate run: it was stored as ONE list
  entry `'src/frob/app/check_runner.py,src/frob/gates/**,tests/**,tickets.md'`
  (comma-joined string, not 4 separate glob entries) from ticket creation,
  so `fnmatch.fnmatch` never matched any of the 4 intended globs and
  SCOPE001 fired on every file this ticket legitimately touches. Split into
  4 separate `scope:` list entries (exactly the paths named in this
  ticket's own dispatch), then re-ran `frob ticket sweep T-0314` (pre-work
  sweep is scope-derived and goes stale when scope changes) before
  `frob check --ticket T-0314` went clean. `tickets.md` is itself in this
  ticket's declared scope, so no new ticket was filed for this fix.

Evidence:
- `tests/system/test_cli_check.py::TestCheckDocAnchorScopedVsUnscoped::test_scoped_docanchor_matches_unscoped`
  (recorded via `frob ticket evidence T-0314 <node id>`)
- `uv run pytest tests/system/test_cli_check.py tests/unit/test_check.py -q`
  -> collected+passed, no failures (ran twice: once standalone for the new
  test, once for the full module pair)
- `uv run pytest tests/test_gates.py -q` -> full pass (docanchor/doclink
  unit tests unaffected by the signature-stable change)
- `uv run ruff check src/frob/gates/__init__.py tests/system/test_cli_check.py`
  -> All checks passed
- `uv run ruff format --check src/frob/gates/__init__.py tests/system/test_cli_check.py`
  -> 2 files already formatted
- `uv run ty check src/frob/gates/__init__.py` -> All checks passed
- `make coverage` -> full suite green, `stamp_coverage: stamped 391 file(s)`
- `uv run frob check` (unscoped, repo root) -> `gates 0 errors, 0 warnings,
  204 waived` (pre-existing waived debt, unchanged); `0` DOC002 occurrences
- `uv run frob check --only gates src/frob/strata` (spot-check scoped run
  named in the dispatch) -> `0` DOC002 occurrences (122 errors present, all
  pre-existing TEST001/TEST003/TEST006 unrelated to this ticket)
- `uv run frob check --ticket T-0314 --only gates` -> `gates 0 errors, 0
  warnings, 204 waived` after the scope-field fix + `frob ticket sweep`
- `uv run frob check --ticket T-0314` (full stage set) -> `gates 0 errors,
  0 warnings, 204 waived`; ruff/ty/exports/gates all `pass`
- `git diff main --diff-filter=D --stat` -> empty (deletion-filter land
  rule clean)

Filed: none (the one out-of-scope-looking discovery, T-0314's own malformed
scope field, was fixed in-scope via `tickets.md`, which this ticket already
declares in its `scope`).

Gates: `frob check --ticket T-0314` clean (0 errors, 0 warnings; the 204
waived entries are pre-existing debt with recorded reasons, none newly
introduced by this change).
