## Done report

Added `frob release publish [--dry-run]` (src/frob/release/_publish.py's
`publish`, `PublishPlan`, `PublishReport`), replacing Makefile's
`upload:` bash recipe (`set -a && . ./.env && set +a` dotenv sourcing,
`uv run python scripts/bump_version.py`, `frob release stamp`/`sync`, a
hand-rolled `git add`/`commit`/`push`, `uv build && uv publish`).

SAFETY (non-negotiable per the brief): NEVER read/cat/echo/print
`.env` contents at any point during this ticket's own work -- did not.
`.env` is loaded via `python-dotenv`'s `load_dotenv()`, called only on a
REAL (non-dry-run) run, never on `--dry-run` (verified by test:
`TestPublish::test_env_only_loaded_on_a_real_run` uses a fake
`pypi-XXXX` placeholder token in a temp `.env`, asserts it is NOT in
`os.environ` after a dry run and IS after a real one). Never performed a
real `git push` or a real PyPI publish at any point verifying this
ticket -- proved entirely via `--dry-run` (a real invocation against a
scratch fixture repo, see below) plus `TestPublish`'s fully argv-stubbed
tests of the real-run path (every `git`/`uv` call replaced with a stub
via `monkeypatch.setattr("frob.gitio.run_argv", ...)`, so no subprocess
of any kind actually spawns in that test).

Cross-platform (T-1205 acceptance[3]/T-2242's own instruction): every
git/uv step is an argv list through `frob.gitio.run_argv`
(`_run_step`/`_sync_derived_artifacts` in `_publish.py`) -- no
`shell=True`, no `bash -c`, no POSIX-only tool. Verified by reading the
implementation (grep for `shell=True`/`subprocess.` in the new module:
none).

`bump_patch_version`/`next_patch_version`/`current_version` (src/frob/
release/__init__.py) are the new canonical single-home implementation of
the unconditional-patch-bump rule; `scripts/bump_version.py` is now a
thin CLI wrapper over `bump_patch_version` (verified with a real
subprocess run against a scratch fixture: bumped 5.6.7 -> 5.6.8
correctly). `frob release publish` calls `bump_patch_version` as a
direct Python function call, never by spawning that script.

CLI wiring is a direct-dispatch special case in `frob.__main__._dispatch`
(`_is_release_publish`), mirroring `bind`/`agent`/`worktree`/
`sync-skills`/`refactor`'s own precedent -- NOT an extension of
`frob.app.release_runner`'s existing `stamp`/`check`/`sync`
`AppConfig`-routed dispatch, since T-2242's own declared scope
deliberately excludes `src/frob/app/release_runner.py` and
`src/frob/_cli_parsers/**` (only `src/frob/release/**` plus
`scripts/bump_version.py`/`Makefile`/docs/tests). `add_release_publish_
parser`/`run_release_publish_command` (new `src/frob/release/_cli.py`)
follow the exact shape `frob.refactor._cli.add_refactor_parser`/
`run_refactor_command` already established for a subcommand dispatched
this way -- that file (in-scope: `src/frob/release/**`) plus two small
`__main__.py` edits (implicit FEATURE-kind CLI-wiring grant, T-0446/
T-1848) were sufficient; no `app.py`/`_cli_parsers/**` touch needed.

Verified end-to-end with real CLI invocations against a scratch fixture
repo (never the real repo, never a real push/publish):

    $ uv run frob release publish --dry-run
    release publish --dry-run: would bump 1.2.3 -> 1.2.4
      would commit: pyproject.toml, uv.lock, CHANGELOG.md, .frob-release.json
      would push, build, and publish

and confirmed `pyproject.toml` was byte-for-byte unchanged afterward.
`frob release publish --help` shows the expected usage.

Makefile `upload:` is now:

    upload: clean
    	uv run frob release publish

MUST-STILL-PASS: `frob release stamp`/`check`/`sync` (the already-landed
verbs this leaf composes into `publish`, never replaces) keep their
existing standalone CLI behavior -- untouched, since `publish`'s own
dispatch is a separate special case that never reaches
`release_runner.py`. `make -n <target>` for every OTHER target (all/
check/test/test-fast/test-unit/test-integration/test-system/format/
lint/lint-fix/typecheck/coverage/coverage-fast/sync-skills/playbook/
deploy-audit/pool-warm/pool-lease/pool-status) all print their expected
commands, unaffected.

Disclosed dependency-fragility note: `python-dotenv` (import name
`dotenv`) is currently satisfied only TRANSITIVELY via
`pydantic-settings`'s own dependency, not declared directly in
`pyproject.toml` -- it works today (verified: `import dotenv` succeeds
in this worktree's venv) but is not a guaranteed dependency of `frob`
itself. `pyproject.toml` is outside this ticket's declared scope; adding
`python-dotenv` as a direct dependency is a one-line follow-up someone
with pyproject.toml in scope should make if this transitive path is ever
unpinned.

### Changed
```
 tickets/T-2242/ticket.md | 61 ++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 57 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_release.py::TestCurrentVersion::test_reads_pyproject_version` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestCurrentVersion::test_missing_pyproject_is_bad_version` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestCurrentVersion::test_never_mutates_the_file` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestNextPatchVersion::test_increments_patch_component` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestNextPatchVersion::test_malformed_version_is_bad_version` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestBumpPatchVersion::test_bumps_and_writes_pyproject` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestPublish::test_dry_run_does_not_mutate_anything` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestPublish::test_real_run_composes_every_step_in_order` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestPublish::test_step_failure_stops_the_sequence_and_reports_the_error` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestPublish::test_env_only_loaded_on_a_real_run` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestRunReleasePublishCommand::test_dry_run_prints_the_plan_and_exits_0` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestRunReleasePublishCommand::test_publish_failure_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestAddReleasePublishParser::test_registers_release_publish_with_dry_run_flag` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC001@docs/commands/release.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t1382-makefile/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t1382-makefile/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/scaffold/_skills_sync.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@tests/test_release.py
