## Done report

Added a `## frob sys sync-interface` section to `docs/commands/sys.md`,
documenting the subcommand landed at 5103c0f1 (T-1150) that was never
mentioned there (the T-1150 draft died to ledger-restore cycles during
its land, per the w18-strata3 done report). Covers: what it does and why
(SYS104 going mandatory at T-1113 turned `interface=` attrs into a
hand-maintained mirror that redded main twice), default vs `--check`
mode behavior/exit codes, the repo-root argument convention (matches
`plan`/`doc`/`audit`), the text-editing strategy (in-place, brace-depth
matched, never a full re-serialize), and `frob:describes` anchors for
the public API (`sync_interface_report`/`apply_sync_interface`) and CLI
wiring (`_run_sync_interface`/`_load_sync_interface_report`/
`_finish_sync_interface`). Also bumped the file's intro line from "Four
verbs" to "Five verbs" to list `sync-interface` alongside the other four.

Docs-only ticket, no pytest surface of its own -- per agent-playbook.md
section 5, the existing CLI-dispatch integration test is recorded as
evidence: `tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches`.

Scope: extended from `docs/commands/sys.md` alone to also cover
`src/frob/app/sys_runner.py`, `src/frob/strata/_sync_interface.py`,
`src/frob/strata/_plan.py`, `src/frob/strata/_export.py`,
`src/frob/strata/_sysdoc.py`, `src/frob/strata/_audit.py` -- SCOPE002
requires every `frob:describes` anchor target in this doc file (both the
new sync-interface anchors and every pre-existing anchor already in the
file for plan/doc/export/audit) to be in-scope.

`uv run frob sys sync-interface --check` (dogfooding the tool this
ticket documents, SYS104 mandatory upkeep, agent-playbook.md): "sys
sync-interface: no drift -- every interface= attr is current".

Gates run (chunked, --ticket T-1160):
- gates-fast: clean (0 errors) after the scope-add + sweep refresh.
- gates-native: 5 pre-existing ARCH001/ARCH103 errors (check_runner.py
  _try_check_delta_via_daemon, _close_cmd.py _fail, doctor.py
  run_diagnosis, _setters.py ticket_flow) -- the same T-1162 baseline
  findings seen on T-1157, none in files this ticket touches.
- gates-security: clean (0 errors).
- lint/static: ruff-check/ruff-format/ty failures are all pre-existing,
  in files this ticket never touched; `docs/commands/sys.md` is markdown
  (not ruff/ty scope) and `ruff check docs/commands/sys.md` reports "No
  Python files found" / "All checks passed!".

`git diff main --diff-filter=D --stat` is empty.

### Changed
```
 tickets.md | 73 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 69 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
