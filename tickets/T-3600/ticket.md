---
id: T-3600
title: 'claude-config-drift fails structurally on CI: 9 managed files read as missing
  where ~/.claude does not exist'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/sync-claude-config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Both POSIX legs of run 33439890956: after a fully green suite
(13074 collected, 0 failed), `uv run frob check` fails with, among the
31 gate errors:

  FAIL  claude-config-drift  9 managed Claude-config file(s) drifted or missing

On a CI runner ~/.claude does not exist, so every 'materialized copy'
of .claude/hooks/* etc. reads as missing -- the check measures the
RUNNER's home, not the repo. This is a portability bug (a gate must
declare where it can run): on a machine with no ~/.claude the correct
verdict is NOT_APPLICABLE/skipped-loud, not FAIL.

Fix: in the claude-config-drift check, detect absence of the
materialization root (~/.claude or $CLAUDE_CONFIG_DIR) and report
NOT_APPLICABLE with a loud one-line note instead of FAIL; keep FAIL for
a PRESENT-but-drifted copy. Add a unit test for the no-home case.
This is one of the errors keeping the POSIX self-gate step red, so it
gates the release bar.