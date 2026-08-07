## Done report

Added `load_repo_benign_capabilities(root)` in `src/frob/strata/_threat.py`:
reads `frob.toml`'s `[[strata.benign_capabilities]]` array of tables (the
same array-of-tables shape `[[policy.*]]` already uses); missing
file/table is `Ok(())`; a malformed entry (missing `kind`/blank `reason`,
unparseable TOML) is `Err(StrataError.MalformedBenignConfig)` (new
`StrataError` member, `_errors.py`). Wired into `frob sys audit` via
`src/frob/app/sys_runner.py::_evaluate_audit`, which now merges
`DEFAULT_BENIGN_CAPABILITIES + load_repo_benign_capabilities(root)`
before calling `evaluate_exhaustiveness`. Exported from
`frob.strata.__init__`. Documented: new "Per-repo benign-capability
declarations" section in `docs/strata/threat.md` (design rationale: TOML
config chosen over a `.strata` grammar addition -- the excuse is repo
configuration about which catalog gaps are accepted, not a model-level
claim about a node's behavior, matching `[graph].exclude`/`[vet.allow]`/
`[[policy.*]]`'s existing register) and a new "Per-repo declarations"
section in `docs/guides/extending/benign-capabilities.md` with a worked
TOML example.

Evidence: recorded via `frob ticket evidence` (7 ids in the ticket's
`evidence:` list above), collected from a fresh `pytest --collect-only`
pass.

Filed: none (closeable within the declared scope).

Gates:
- `uv run pytest tests/unit/strata/test_threat.py -q`: all green.
- `uv run pytest -q` (full repo): all green.
- `uv run frob check --stamp-baseline`: `gates 0 errors, 0 warnings, 204
  waived` -- clean baseline stamped (0 violations over 26012 files).
- `uv run frob sys audit`: `sys audit: PROVED (5 waived) -- zero UNWAIVED
  gaps across every configured view`; `sys audit: self-conformance
  PROVED -- zero SYS gaps`.
- `git diff main --diff-filter=D --stat`: empty (deletion-filter clean).
