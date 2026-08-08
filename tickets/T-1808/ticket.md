---
id: T-1808
title: Fold Claude-config sync (sync-claude-config.py) into a real frob verb
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
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
