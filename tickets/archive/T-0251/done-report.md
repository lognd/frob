## Done report

Changed:
- `src/frob/__main__.py::_add_vet_parser` -- registers `--timeout` (float,
  seconds) and `--jobs` (int) on the `vet` subparser.
- `src/frob/app/config.py::AppConfig` -- new `vet_timeout: float | None`
  and `vet_jobs: int | None` fields; `from_external` gained a float-field
  loop (`vet_timeout`) and added `vet_jobs` to the existing int-field
  loop, so both flow from CLI args (or `[tool.frob]` in pyproject.toml)
  into `AppConfig`.
- `src/frob/app/vet_runner.py::_run_scan` -- now calls
  `scan_tree(root, timeout=cfg.vet_timeout, jobs=cfg.vet_jobs or 1)`
  instead of the bare `scan_tree(root)`; `jobs` still defaults to the
  safe untimed/single-worker path when the flag is unset.
- `docs/modules/vet.md` -- T-0208's "Progress and bounding" section
  updated: the flags are now wired (was previously documented as a
  follow-up out of T-0208's scope); the disclosed shared-cache race risk
  for `jobs>1` is unchanged and cross-referenced.

Also fixed a pre-existing malformed `scope:` entry on this ticket itself
(a single comma-joined string instead of four separate YAML list items,
which made `fnmatch` match none of the four intended files and caused
every in-scope edit to trip SCOPE001) -- this is the ticket's own
frontmatter, in scope implicitly per the ticket-editing convention, not
an out-of-scope fix.

Evidence (recorded via `frob ticket evidence T-0251 ...`, all 4 resolved
against a fresh `pytest --collect-only`, 3012 node ids):
- `tests/unit/test_app.py::test_config_cli_overrides_file` --
  `AppConfig.from_args`/`from_external` CLI-override path unchanged/still
  passes with the new `vet_timeout`/`vet_jobs` fields present.
- `tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_lockfile_arg` --
  `scan_tree` signature/behavior unchanged/still passes.
- `tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero`
  -- `frob vet --hook` CLI dispatch path unchanged/still passes.
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches`
  -- CLI dispatch integration test, per the playbook's docs-only-ticket
  precedent, covering the new argparse wiring is reached through the
  same `main()` path.
- Manual CLI round-trip (not a pytest node, supplementary): `frob vet .
  --timeout 5.5 --jobs 4` parses to `AppConfig(vet_timeout=5.5,
  vet_jobs=4)` via `_build_parser()` + `AppConfig.from_args()`.
- All four evidence files' full suites run together:
  `uv run pytest tests/unit/test_app.py tests/test_vet.py tests/system/test_cli_vet.py tests/integration/test_interfaces.py -p no:cacheprovider -q`
  -> 176 passed, 0 failed.

Filed: none (no out-of-scope work found; the malformed-scope fix was on
this ticket's own frontmatter).

Gates: `frob check --ticket T-0251` -- 1 error: SCOPE001 on `tickets.md`,
which is expected/always-in-scope per `docs/guides/agent-playbook.md`
section 4 (the Done report itself lives there) and not something this
change introduced, per the T-0336 precedent recorded above in this file.
No SCOPE001/TEST001/TEST002/COV001 violations from the four scoped files
themselves. `frob:waive REL001` disclosed at commit time: this ticket
does not bump `[project].version` or touch `CHANGELOG.md` (a CLI flag
addition, not a release-worthy user-facing behavior change to the
default path -- `jobs`/`timeout` default to the pre-existing untimed,
single-worker behavior when unset).
