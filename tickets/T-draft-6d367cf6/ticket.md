---
id: T-draft-6d367cf6
title: 'frob format rewrites files outside the current ticket scope: add a scope-limited
  mode (automatic under a ticket lease) and --all to opt out'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/app/pyfmt_runner.py
- src/frob/_cli_parsers/
- docs/modules/format.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external or future-facing paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 971
  new_length: 1077
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26): while working T-0176, `frob
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->format` rewrote src/crunk/__main__.py and src/crunk/rules/_breakpoints.py,
pre-existing repo-wide ruff drift outside the ticket's declared scope, and
the agent had to `git checkout --` them by hand. Verified on dev
b41443f46d: `frob format --help` offers --code/--directives/--check/--json/
--select-imports-only/--include-test-corpora, no scope or ticket limit.

Deliver (tiered safety): when the invocation runs inside a worktree with a
live ticket lease, format only the lease's scope plus the worktree's
touched files automatically and log one line naming the ticket and the
file count; `--all` opts back into the whole tree (explicit flag); outside
a lease behaviour is unchanged. `--check` follows the same scoping.
Positive control: a fixture with one in-scope and one out-of-scope
misformatted file under a planted lease; format rewrites exactly the
in-scope one, and `--all` rewrites both.
