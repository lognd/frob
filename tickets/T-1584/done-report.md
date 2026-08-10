## Done report

MEASURED FIRST, per the coordinator's warning about a parser flag being
DEFINED but unreachable: `frob profile --help` genuinely errored with
"invalid choice: 'profile'" against current main -- the subcommand did
not exist at all, no argparse entry, no runner. `frob.tickets._profile`'s
public API (`configured_profile`, `effective_profile`,
`downgrade_profile_ratchet`) had zero callers anywhere in src/ (grepped)
except its own module and tests. This was genuinely absent, not merely
unreachable -- no wrong-ticket risk to disclose here.

WIRED (T-1584):
- `Subcommand.profile` (src/frob/app/config.py) + `AppConfig` fields
  (profile_command, profile_path, profile_json,
  profile_downgrade_reason, profile_downgrade_reason_file) -- mirrors
  the existing `registry_command`/`fleet_command` show/action-pair shape
  exactly, not a new pattern.
- `_add_profile_parser`/`_populate_profile_actions`
  (src/frob/_cli_parsers/_reporting.py): `frob profile show` /
  `frob profile downgrade --reason TEXT|--reason-file PATH`, mirroring
  `_add_registry_parser`'s subparsers-with-dest shape.
- `src/frob/app/profile_runner.py` (new): `run(cfg)` dispatches
  show/downgrade. `show` calls `configured_profile`/`effective_profile`
  (read-only). `downgrade` is the ONLY caller of
  `downgrade_profile_ratchet` in the whole package outside its own
  tests -- matches T-1575's module docstring's "downgrades never
  automatic" contract exactly, since this CLI command is itself always
  an explicit human/agent decision, never invoked from a land-pipeline
  seam.
- Registered in `frob.app.app._SUBCOMMAND_RUNNER_NAMES`/
  `_import_runner_module`'s closed if/elif chain, and
  `frob.app.__init__._RUNNER_RUN_MODULES`/`__all__` (parity with every
  other runner's lazy-import alias).
- `_config_external.py`: added the four new field names to the
  string/path/bool argparse-Namespace-to-AppConfig copy allowlists --
  MEASURED this was required (a first smoke-test of `frob profile
  downgrade --reason x` silently landed on the SHOW branch, because
  `profile_command` never reached `cfg` without this registration; not
  assumed, caught by running the actual command).

`--reason-file` follows T-0737's shell-injection-avoidance precedent
(verbatim, single read -- section 1d/T-2021's own lesson: resolved
exactly once, no double-read hazard).

`--json` output goes through `_log.info(json.dumps(...))`, not a bare
`print`, matching `frob debt`'s own RENDER001-conscious convention
(tests/test_debt_runner.py's documented rationale) -- caught by reading
an existing runner's test file before writing my own, not assumed.

Evidence (feature-kind, no BUG002 repro applicable):
9 new tests in tests/unit/test_profile_runner.py covering show
(plain/json/bare-defaults-to-show/reports-a-real-persisted-ratchet) and
downgrade (requires-a-reason/mutual-exclusion/clears-a-real-ratchet/
reason-file-read-verbatim/no-op-when-nothing-ratcheted).
`tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality`
(pre-existing, parametrized over every `Subcommand` member) exercised
directly and PASSED with the new `Subcommand.profile` member added --
this is the exhaustive totality check T-1319 built specifically to
catch a new subcommand added without a matching runner registration; it
caught nothing wrong here, confirmed by running it, not assumed clean.

Ran (measured):
`uv run pytest tests/unit/test_profile_runner.py
tests/unit/test_app_lazy_dispatch.py -q` -- 53 passed
(9 + 44), 0 failed.
`uv run frob check --ticket T-1584 --only test`: 0 errors, 25 warnings
(pre-existing, unrelated), 7 waived (pre-existing).
`uv run frob check --land-parity`: clean -- 0 unscoped error(s).
Live CLI smoke test (not just unit tests): `frob profile show`,
`frob profile show --json`, `frob profile downgrade` (no reason,
refuses with exit 1), `frob profile downgrade --reason ...` (against a
manually-written real ratchet file, genuinely cleared it, then `show`
confirmed effective flipped back to rapid) -- all run directly against
this worktree's own real `.frob/`, not mocked.

Corrected mid-ticket (self-caught, not coordinator-flagged): my test
file's own self-referential `# frob:tests` comments initially used
pytest's `path::Class::method` invocation syntax; this repo's directive
convention is `path::Class.method` (single `::` after the path, dot
between class and method) -- DRIFT002 caught the mismatch on the first
scoped check, fixed by rewriting all 9 directives to the dot form,
re-verified 0 DRIFT errors after.

### Changed
```
 tickets/T-1584/ticket.md | 87 ++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 84 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/app/profile_runner.py, ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1584, SELFAUDIT001@design, WIRE001@tests/unit/test_profile_runner.py
