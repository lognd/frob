## Done report

Changed:
- src/frob/__main__.py::_frob_version (new) -- resolves `frob --version`
  from package metadata (`importlib.metadata.version("frob")`)
- src/frob/__main__.py::_build_parser -- registers `--version`
- src/frob/app/sys_runner.py::_print_dry_run -- prints
  "DRY RUN (no tickets created; pass --apply to compile)" plus the count,
  naming --apply explicitly, before the dry-run ticket-tree listing
- src/frob/gates/__init__.py::_doclink_root_hint (new) -- resolves the
  DOC001 orphan-doc hint against a docs root that actually exists on
  disk, falling back to "create it" / "none configured" instead of
  blindly naming docs/index.md
- src/frob/gates/__init__.py::doclink_gate -- uses the new hint helper

Evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_version_flag_prints_version_and_exits_zero
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dry_run_names_apply_flag_in_label
- tests/test_gates.py::TestDoclinkGate::test_orphan_hint_does_not_point_at_missing_docs_root
- Full suite: `uv run pytest tests/ -q -n auto` -- all pass (no failures)
- `uv run ruff check` / `uv run ruff format --check` -- clean (both PATH
  ruff and `uv run ruff`)
- `uv run ty check src/` -- no issues

Filed: none (no out-of-scope work discovered)

Gates: `uv run frob check` -- 2 remaining ERROR-severity violations, both
pre-existing and unrelated to this ticket, verified present on bare
`main` (591502e) before any of this ticket's changes:
- DRIFT002 x2 at tests/test_graph.py:538,551 (TestMalformedFileVisibility
  stale `.`-vs-`::` qualname refs, predates T-0231, left from T-0216)
No new violations from this ticket's changes.

REL001 disclosure: adding `--version` is new public CLI surface, which
tripped REL001 (public API changed since 0.3.0, needs >=0.4.0 + a
CHANGELOG entry + `.frob-release.json` stamp). Per this ticket's explicit
authorization, bumped pyproject.toml to 0.4.0 and ran `frob release
stamp` -- disclosing here since this is normally out of a small CLI-fix
ticket's remit, but the gate hard-blocked without it. `main` independently
bumped to 0.4.0 for T-0209/T-0212/T-0253 in the interim; after merging
main, reconciled by folding T-0231's CHANGELOG line into the single
existing `[0.4.0]` section (no competing section) rather than re-bumping.

Round 2 (reviewer fix): corrected the `_print_dry_run` frob:tests
directive from an invalid `kind="system"` (silently dropped as
malformed, leaving no real graph edge) to `kind="integration"`; merged
`main` (T-0209/T-0212/T-0253, already at 0.4.0) and reconciled the
CHANGELOG conflict by keeping main's `[0.4.0]` section and appending the
T-0231 line to it; reverted worktree contamination
(`src/frob/vet/_capability.py`, `src/frob/lang/__init__.py`,
`tests/test_vet.py`) that had leaked in from an unrelated concurrent
stash and already landed via T-0209 on main -- worktree is now clean of
anything not this ticket's.
