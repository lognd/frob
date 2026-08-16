## Done report

Added `frob sync-skills` (src/frob/scaffold/_skills_sync.py -- `sync_skills`
the pure logic, `run` the CLI entry point), replacing Makefile's
`sync-skills:` bash recipe (two POSIX `for` loops copying agents/skills
in, two more removing stale entries, `basename`, `[ -d ]`). Pure
pathlib/shutil: `shutil.copytree(src, dst, dirs_exist_ok=True)` for
create-or-update, `shutil.rmtree` for stale-entry removal -- no shelled-
out loop, no POSIX-only tool, verified by reading the implementation
(no `subprocess`/`shell=True` anywhere in the module).

CLI wiring mirrors `bind`/`agent`/`worktree`'s own precedent (T-0355/
T-0574/T-0836), not `frob.app.app`'s uniform `AppConfig`-based runner
registry: `frob.__main__._dispatch` special-cases `argv[0] ==
"sync-skills"` and calls `frob.scaffold._skills_sync.run(argv[1:])`
directly. `_add_sync_skills_parser` (src/frob/_cli_parsers/_misc.py) is
still registered normally in `_build_parser()`'s subparser tree so
`frob --help`/`frob sync-skills --help` discover it, exactly like
`bind`'s own dual registration -- but the real invocation never reaches
`AppConfig`. This was a deliberate scope choice: T-2241's declared scope
covers `_misc.py`/`_cli_parsers/__init__.py` but not `src/frob/app/app.py`
or a new `app/*_runner.py` file, and the direct-dispatch pattern needs
neither -- `__main__.py`'s implicit FEATURE-kind CLI-wiring grant (T-0446/
T-1848) covers the two lines this needed there.

Verified end-to-end with a real CLI invocation against a temp directory
(not `~/.claude`):

    uv run frob sync-skills <tmp-repo> --claude-dir <tmp-claude>

correctly synced new entries, updated an existing one in place, and
removed a stale claude-side entry with no repo-side counterpart.
`frob sync-skills --help` and `frob --help`'s subcommand listing both
show it.

Makefile `sync-skills:` is now:

    sync-skills:
    	uv run frob sync-skills

Removed the now-dead `CLAUDE_DIR := $(HOME)/.claude` variable (no other
recipe read it).

MUST-STILL-PASS: `make -n <target>` for every OTHER target (all/check/
test/test-fast/test-unit/test-integration/test-system/format/lint/
lint-fix/typecheck/coverage/coverage-fast/playbook/deploy-audit/
pool-warm/pool-lease/pool-status/upload) all print their expected
commands, unaffected.

The stale-entry-removal MUST-STILL-PASS the ticket names explicitly is
proven by `TestSyncSkills::test_removes_stale_claude_side_entry`
(temp-directory `claude_dir`, never the real `~/.claude`) -- verified
passing here.

Docs: added docs/commands/sync-skills.md (usage, behavior, error
handling, public API -- matching this repo's existing docs/commands/*.md
shape).

### Changed
```
 tickets/T-2241/ticket.md | 28 +++++++++++++++++++++++++---
 1 file changed, 25 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_syncs_new_repo_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_updates_existing_entry_in_place` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_removes_stale_claude_side_entry` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_missing_repo_directories_are_a_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestSyncSkills::test_files_directly_under_claude_dir_are_left_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestRun::test_run_reports_synced_and_removed_counts` (pytest node id, verified passing when recorded)
- `tests/unit/test_skills_sync.py::TestRun::test_run_defaults_to_home_claude_when_no_override_given` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t1382-makefile/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t1382-makefile/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@src/frob/_cli_parsers/_misc.py
