## Done report

T-4521 -- ticket verb family cleanup: Done narrative
=====================================================

What changed
------------

1. Hidden internal callbacks (merge-driver, sweep-async)
   - Measured that argparse.SUPPRESS on a subparser's `help=` at
     creation time does NOT hide it from `--help` in cpython 3.10-3.12:
     HelpFormatter._format_action recurses into every subaction
     unconditionally and prints the literal "==SUPPRESS==" string. The
     actual mechanism is removing the subcommand's pseudo-action from
     `_SubParsersAction._choices_actions` entirely (dispatch, which
     reads `_name_parser_map`, is untouched). Wrote
     `_suppress_subparser_alias` in _progress.py to do this correctly,
     used it for merge-driver (created normally, then suppressed) and
     for sweep-async (built in the leased _closeout_evidence.py by the
     existing import, suppressed post-hoc from __init__.py, which IS
     in scope).
   - Verified: `git grep -n merge-driver -- .gitattributes docs` still
     shows the unchanged `merge.frob-ledger.driver` invocation string
     (`uv run frob ticket merge-driver %O %A %B`) -- the git callback
     path is untouched, only --help visibility changed.

2. migrate / debt / deprecated removal
   - Added `_removed_verb_notice(old, replacement)` in
     ticket_runner/__init__.py; migrate/debt/deprecated dispatch table
     entries now point at thin wrappers that call it and exit 2.
   - The underlying `_migrate` import (unused now) and its lambda
     dispatch entry were removed. `debt_runner.run`/`deprecated_runner
     .run` are no longer called from this path (the standalone `frob
     debt`/`frob deprecated` commands are untouched -- they don't go
     through ticket_runner at all).
   - REGRESSION FOUND AND FIXED (in scope, added via frob ticket
     scope --add, unleased): tests/test_tickets_migration.py's
     TestMigrateCliToV2Flag/TestMigrateCliFillGapsFlag (5 tests) and
     tests/unit/test_app_runners_batch7.py's debt/deprecated/migrate
     dispatch tests (5 tests) all called `ticket_runner.run(cfg)` with
     `ticket_command="migrate"/"debt"/"deprecated"` and asserted the
     OLD behavior actually ran. Since removing the verb is deliberate,
     I rewrote these 10 tests to assert the new removal-notice/exit-2
     behavior instead. The underlying engine functions
     (migrate_v1_to_v2, migrate_missing_v2) are untouched and still
     covered directly by TestMigrateV1ToV2/TestMigrateMissingV2 in the
     same file, which call the functions directly, not through the CLI
     dispatch path.
   - COORDINATOR FOLLOW-UP (addressed, second commit): the land runs an
     orphan-evidence check -- any test node id cited as evidence by ANY
     ticket (T-1492/T-2728 included, both already `done`) must still
     resolve, or the land is refused. My first pass had renamed the
     classes/methods (TestMigrateCliToV2Flag/TestMigrateCliFillGapsFlag
     -> TestMigrateCliRemoved, and 5 debt/deprecated/migrate methods to
     new names), which broke those citations. Restored the ORIGINAL
     class names and all 9 original method names in both files (see
     `git diff dev -- tests/test_tickets_migration.py
     tests/unit/test_app_runners_batch7.py | grep '^-.*def test_'` --
     now empty of any genuinely-removed name), keeping the NEW
     removal-notice/exit-2 assertions inside each -- each renamed-back
     test got a one-line docstring saying it now covers the removed
     verb instead of its original behavior. Re-ran the serial suite for
     both files (145 passed) plus the full combined set (194 passed),
     confirmed ruff/ty clean, committed separately (second commit,
     771ace4f563a016fb6252646a1b00b698dd2ae04), confirmed
     `git status --short` empty again.

3. runs-last --parallel-safe (folding runs-last-parallel-safe) --
   NOT DONE, DEFERRED (coordinator will fold into T-3614 once
   config.py's lease clears -- no further action needed from this
   ticket)
   - The fold requires a new `ticket_runs_last_parallel_safe_flag`
     field on `AppConfig` (src/frob/app/config.py) -- pydantic
     BaseModel with an explicit copy-loop in
     `_build_external_config_kwargs`/`from_external`, not a
     permissive/extra="allow" model, so an undeclared argparse dest
     never reaches `cfg`. That file is under an in-progress lease held
     by T-draft-0b42af92 (scope: src/frob/app/config.py,
     src/frob/__main__.py). Confirmed via
     `frob ticket scope T-4521 --add src/frob/app/config.py`, which
     refused with ScopeLeaseConflict naming T-draft-0b42af92. Per hard
     rule ("a lease refusal naming another ticket means stop and
     report, never --steal"), left runs-last-parallel-safe exactly as
     it was (both the CLI verb and its AppConfig fields untouched, no
     partial/broken state). Documented the block in
     docs/commands/ticket.md under its own "STATUS: NOT YET FOLDED"
     section so it isn't silently forgotten. This is criterion 3 of
     4 -- NOT satisfied. Recommend a follow-up ticket once
     T-draft-0b42af92 lands/releases the config.py lease; happy to file
     it if wanted (did not file it unprompted since the coordinator may
     prefer to fold it back into T-4521 itself once unblocked, or spin
     a new one -- your call).

4. admin group: renumber, restore, reconcile
   - `_add_ticket_reconcile_parser` factored out of
     `_add_ticket_progress_parsers` (was inline) so the same builder
     serves both locations.
   - New `_add_ticket_admin_parser(ticket_sub)` in _progress.py
     registers `admin` with its own sub-subparsers (dest="ticket_command"
     -- SAME dest string as the outer ticket_sub, which is the trick
     that makes `frob ticket admin renumber` end up with
     cfg.ticket_command == "renumber" with ZERO changes needed to the
     dispatch table, _LAND_LOCK_EXEMPT_VERBS, or any other
     verb-keyed logic downstream -- argparse's nested SubParsersAction
     overwrites the outer namespace attribute with the inner one when
     both share a dest).
   - renumber/reconcile: registered fresh under admin_sub via the SAME
     builder functions used for their (now hidden) top-level aliases --
     byte-for-byte identical argument specs by construction.
   - restore: its builder lives in _closeout_evidence.py (leased by
     T-draft-db13b6bc, scope includes that exact file). Could not call
     its builder a second time. Instead reused the ALREADY-BUILT
     top-level `restore` ArgumentParser object (from the existing,
     unedited call to _add_ticket_fail_evidence_archive_parsers in
     __init__.py) by registering the SAME instance into admin_sub's
     `_name_parser_map` and adding a matching `_ChoicesPseudoAction` for
     help listing -- confirmed safe (argparse actions/parsers carry no
     back-reference to their owning subparsers action) and verified
     byte-for-byte identical by construction (literally the same
     object, not a re-implementation) in
     test_admin_restore_matches_hidden_top_level_alias.
   - Old top-level renumber/reconcile/restore spellings suppressed via
     `_suppress_subparser_alias` (still fully dispatchable).

Lease conflicts encountered (both correctly stopped-and-reported, not
stolen):
  - src/frob/_cli_parsers/_ticket/_closeout_evidence.py -- leased by
    T-draft-db13b6bc. Narrowed T-4521's directory-glob scope down to
    the individual files in that directory MINUS this one at the very
    start (before `ticket start`), so the ticket could even begin.
    Worked around it for sweep-async (post-hoc help suppression) and
    restore (shared parser-object reuse) without ever touching the
    file.
  - src/frob/app/config.py -- leased by T-draft-0b42af92. Blocks
    criterion 3 entirely (see above). Not worked around -- there is no
    clean way to get a new field into a strict pydantic model without
    editing its definition.

Tests
-----
New: tests/unit/test_ticket_cli_surface.py (12 tests) -- covers all
four acceptance criteria at the argparse-tree/dispatch-handler level
(no subprocess, no git repo, no file I/O): hidden-but-dispatchable for
merge-driver/sweep-async, exit-2 removal notices for migrate/debt/
deprecated, and byte-for-byte admin-vs-alias equivalence for
renumber/restore/reconcile (criterion 3 has no new test since it is
not implemented).

Updated (regression fix, in scope; then names restored per coordinator
request so T-1492/T-2728's cited evidence node ids still resolve):
  tests/test_tickets_migration.py -- TestMigrateCliToV2Flag (2 tests:
    test_migrate_to_v2_flag_calls_migrate_v1_to_v2,
    test_migrate_without_to_keeps_dir_collapse_behavior) and
    TestMigrateCliFillGapsFlag (3 tests:
    test_fill_gaps_flag_calls_migrate_missing_v2,
    test_fill_gaps_omitted_keeps_original_behavior,
    test_fill_gaps_combines_with_to_v2) -- original class/method names
    kept, bodies now assert removal-notice/exit-2.
  tests/unit/test_app_runners_batch7.py -- TestTicketRunnerDispatch's
    test_debt_subcommand_delegates_to_debt_runner/
    test_deprecated_subcommand_delegates_to_deprecated_runner, and
    TestTicketMigrate's test_no_legacy_files/
    test_migrates_legacy_dir_ticket -- same treatment, original names
    kept, bodies now assert removal.
  Verified every name `git diff dev -- <these 2 files> | grep
  '^-.*def test_'` used to list is back: 0 names missing.

Full command output (serial, PYTHONPATH pointed at this worktree's src):
  tests/unit/test_ticket_cli_surface.py .......... (12 passed)
  tests/test_tickets_migration.py ................ (20 passed)
  tests/unit/test_app_runners_batch7.py .......... (121 passed)
  tests/test_tickets_organization.py ............. (37 passed)
  Combined (all four files together): 194 passed, 0 failed.

ruff check / ruff format --diff: clean on every touched file (both
commits).
ty check: clean on every touched file (both commits).

git -C <worktree> status --short: empty (everything committed --
commit 1: 3c767b4e696c4a8cade20ade5ce878bdfbb4dd9c "feat(ticket): hide
callbacks, remove migrate/debt/deprecated, add admin group"; commit 2:
771ace4f563a016fb6252646a1b00b698dd2ae04 "fix(ticket): keep old test
node ids alive for orphan-evidence check", both on branch t-4521).
git -C /home/logan/projects/frob status --short: empty (root
untouched throughout).

Acceptance criteria status
---------------------------
1. merge-driver/sweep-async hidden, still dispatch -- DONE, tested.
2. migrate/debt/deprecated removal notice + exit 2 -- DONE, tested;
   old cited evidence node ids in tests/test_tickets_migration.py and
   tests/unit/test_app_runners_batch7.py kept alive per coordinator
   request (orphan-evidence land gate).
3. runs-last --parallel-safe replaces runs-last-parallel-safe --
   BLOCKED by config.py lease (T-draft-0b42af92). Coordinator confirmed
   this stays deferred and will fold it into T-3614 once the lease
   clears -- no further action on this from T-4521.
4. ticket admin renumber|restore|reconcile byte-for-byte, hidden
   top-level aliases for one release -- DONE, tested.

READY for land (1, 2, 4 delivered and tested; criterion 3 explicitly
deferred to T-3614 by the coordinator, not a T-4521 open item anymore).

### Changed
```
 docs/commands/ticket.md                    |  72 ++++++++++++
 src/frob/_cli_parsers/_ticket/__init__.py  |  55 ++++++++-
 src/frob/_cli_parsers/_ticket/_progress.py | 128 +++++++++++++++-----
 src/frob/app/ticket_runner/__init__.py     |  55 +++++----
 tests/test_tickets_migration.py            | 106 +++++++++++------
 tests/unit/test_app_runners_batch7.py      |  97 ++++++++++-----
 tests/unit/test_ticket_cli_surface.py      | 182 +++++++++++++++++++++++++++++
 tickets/T-4521/ticket.md                   |  26 ++++-
 8 files changed, 592 insertions(+), 129 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_cli_surface.py::TestHiddenInternalCallbacks::test_merge_driver_still_dispatches` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_cli_surface.py::TestRemovedVerbsExitTwo::test_migrate_removed_notice_names_replacement` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_cli_surface.py::TestAdminGroup::test_admin_renumber_matches_hidden_top_level_alias` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 24 error(s), 4954 warning(s), 976 waived
- error-findings: ARCH103@src/frob/app/config.py, ARCH103@src/frob/doctor.py, CROSSTICKET001@design/frob.strata, CROSSTICKET001@docs/commands/check.md, CROSSTICKET001@docs/design/registry/capability-via-ratchet.lock.json, CROSSTICKET001@docs/modules/app.md, CROSSTICKET001@docs/modules/lang.md, CROSSTICKET001@docs/modules/tickets-landing.md, CROSSTICKET001@src/frob/_cli_parsers/_check.py, CROSSTICKET001@src/frob/app/_config_external.py, CROSSTICKET001@src/frob/app/check_runner.py, CROSSTICKET001@src/frob/app/config.py, CROSSTICKET001@src/frob/app/ticket_runner/_land_cmd.py, CROSSTICKET001@src/frob/app/ticket_runner/_verify.py, CROSSTICKET001@src/frob/dup/_legacy_cs.py, CROSSTICKET001@src/frob/gates/__init__.py, DOC001@docs/commands/ticket.md, MILE001@tickets.md, PERF004@src/frob/doctor.py, PRE001@tickets/T-4521, REF002@src/frob/vet/_capability_registry/_dotnet_bcl.py, SEC110@src/frob/app/config.py, WIRE002@src/frob/dup/_legacy_cs.py, invalid-argument-type@tests/unit/test_ticket_runner_land_cmd_flags.py

### Acceptance amendments
- [3] remove: removed 'GIVEN frob ticket runs-last --parallel-safe WHEN run THEN it records what runs-last-parallel-safe recorded, and the old verb is gone' (reason: runs-last --parallel-safe deferred into T-3614 by coordinator decision (config.py lease); logan, 2026-09-17)
