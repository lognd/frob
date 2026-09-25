---
id: T-5811
title: 'CI: make core-wheels narrows uv sync to --extra serve, dropping sqlfluff before
  Typecheck (all 3 legs)'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 1
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
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: Makefile
  reason: '$(STAMP): pyproject.toml''s recipe syncs only --extra serve, narrowing
    an already-full uv sync --all-extras --all-groups back down before CI''s Typecheck
    step runs (via make core-wheels'' core -> $(STAMP) dependency chain), dropping
    sqlfluff and breaking ty check on all 3 platforms'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '1'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 36086669322 (dev 2d0da515df). ALL THREE
platform legs (ubuntu/macos/windows) fail at the SAME "Typecheck" step
with identical errors:

  error[unresolved-import]: Cannot resolve imported module `sqlfluff.core.config`
  src/frob/sql/_sqlfluff_plugin.py:45
  (same for sqlfluff.core.plugin, sqlfluff.core.rules, sqlfluff.core.rules.crawlers)

Root-caused directly from the raw job logs: CI's first "Sync deps" step
runs `uv sync --all-extras --all-groups` (installs sqlfluff==3.5.0,
confirmed by the log's own "+ sqlfluff==3.5.0" line). A LATER step,
`make core-wheels` (which depends on the `core` -> `$(STAMP)` Makefile
chain), re-runs `uv sync --extra serve` via the `$(STAMP): pyproject.toml`
rule -- this NARROWS the already-full sync back down to just the "serve"
extra, uninstalling sqlfluff (and chardet/colorama/diff-cover/
platformdirs/regex/tblib/tqdm) before the "Typecheck" step ever runs
(confirmed by the log's own "- sqlfluff==3.5.0" uninstall line
immediately after "uv sync --extra serve").

Because Typecheck fails, every subsequent Test step is skipped on all
three platforms (and self-gate too, except on windows where it runs
`if: always()` and then hits its own separate CacheLocked infra failure
-- see the sibling finding for that, filed/owned separately if not
already).

Fix: `$(STAMP): pyproject.toml`'s recipe (Makefile) syncs a narrower
extra set than CI's own initial full sync assumed would persist through
the rest of the job -- either widen it to match (`--all-extras
--all-groups`), or reorder ci.yml so nothing re-narrows the sync between
the initial "Sync deps" step and "Typecheck".
