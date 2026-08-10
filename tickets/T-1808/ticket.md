---
id: T-1808
title: Fold Claude-config sync (sync-claude-config.py) into a real frob verb
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/app/claude_runner.py
- .claude/hooks/sync-claude-config.py
- docs/modules/cli.md
- src/frob/_cli_parsers/__init__.py
- src/frob/_cli_parsers/_misc.py
- docs/guides/claude-hooks.md
- src/frob/app/_config_external.py
- tests/unit/test_claude_runner.py
- design/frob.strata
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/**
  reason: frob claude sync needs a new top-level argparse subparser; every existing
    verb's parser lives in src/frob/_cli_parsers/, not app.py itself -- omitted from
    the ticket's original declared scope
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: narrowing to specific files after closure-warning fan-out
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: frob claude sync needs a new argparse subparser wired through _cli_parsers
    (existing verbs' add_parser fns live in _misc.py/__init__.py, not app.py); claude-hooks.md
    documents the sync script this ticket folds into a verb
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: frob claude sync needs a new argparse subparser wired through _cli_parsers
    (existing verbs' add_parser fns live in _misc.py/__init__.py, not app.py); claude-hooks.md
    documents the sync script this ticket folds into a verb
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: frob claude sync needs a new argparse subparser wired through _cli_parsers
    (existing verbs' add_parser fns live in _misc.py/__init__.py, not app.py); claude-hooks.md
    documents the sync script this ticket folds into a verb
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/_config_external.py
  reason: AppConfig.from_external's argparse-to-kwargs mapping keys off hardcoded
    _STRING_FIELDS/_BOOL_FLAGS tuples in this file; claude_command/claude_check need
    entries here or the CLI-parsed values never reach AppConfig
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_claude_runner.py
  reason: new direct-call test module for claude_runner (T-1808)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: new test module's fs.read/fs.write capabilities need declaring in the testsuite
    node's may clauses (SELFAUDIT001)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: README.md
  reason: gate:DOC005 requires the new frob claude command in README.md's own hand-maintained
    command table alongside cli.md's generated one
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_claude_runner.py::TestDriftReport::test_reports_drifted_and_missing
- tests/unit/test_claude_runner.py::TestDriftReport::test_none_for_repo_with_no_managed_config
- tests/unit/test_claude_runner.py::TestDriftWarning::test_warns_when_managed_file_differs
- tests/unit/test_claude_runner.py::TestDriftWarning::test_none_when_in_sync
- tests/unit/test_claude_runner.py::TestDriftWarning::test_none_when_repo_has_no_managed_config
- tests/unit/test_claude_runner.py::TestRun::test_check_mode_exits_1_on_drift
- tests/unit/test_claude_runner.py::TestRun::test_sync_writes_managed_files
- tests/unit/test_claude_runner.py::TestRun::test_run_rejects_unknown_action
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1719 implemented only the doctor-side global-vs-local frob binary skew
check (its item 3). Items 1 and 2 of T-1719's original plan are still
open and were deliberately cut from that ticket's scope:

1. FOLD THE SYNC INTO frob: a verb (`frob claude sync` / `frob agent
   sync`) that reads a managed-file manifest from frob.toml and replaces
   the loose `.claude/hooks/sync-claude-config.py` script, writing each
   destination behind the do-not-edit banner atomically, never syncing
   global -> repo, `--check` naming every drifted path.

This needs a new top-level subcommand wired through `src/frob/app/app.py`
(`_RUNNER_MODULE_NAMES`/`_SUBCOMMAND_RUNNER_NAMES`/`_import_runner_module`),
`src/frob/app/config.py` (the `Subcommand` enum), and a new
`src/frob/app/claude_runner.py` (or similarly named) module -- none of
which were in T-1719's narrowed scope (doctor.py/cli.md/test_doctor.py
only). Be precise about WHICH `~/.claude/` files are repo-owned: only
`.claude/hooks/*.py` and `docs/guides/agent-playbook.md` are git-tracked
in this repo and materialized outward by `sync-claude-config.py`'s
`_MANAGED` list -- `~/.claude/` also holds agent and skill definitions
that are user-scope only and this repo does NOT own or sync (a prior
audit wrongly concluded this repo's own `agents/`/`skills/` directories
were live-read when nothing reads them; do not conflate the two).

The BLOCK-ONCE-THEN-ALLOW semantics in `.claude/hooks/frob-suggest.py`
must be preserved exactly when its rule table moves with the sync verb.