+++
id = "01M35RZY9W2GB6D77S2AVNR1P8"
title = "Hook: deny self-matching pgrep -f pollers in Bash tool calls"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5436"]
labels = ["milestone:v0.534.0"]
scope = [".claude/hooks/pgrep-self-match-guard.py", ".claude/hooks/_shellscan.py", ".claude/hooks/sync-claude-config.py", ".claude/settings.json", "docs/guides/claude-hooks.md", "tests/test_hook_pgrep_self_match_guard.py"]
+++

Measured 2026-09-23: 26 of about 40 live harness shells were poll loops that could never exit. 18 were `until ! pgrep -f "<literal>"` / `while pgrep -f "<literal>"` loops written by implementer agents: the literal pattern appears in the polling shell's own `bash -c` command line, so pgrep always matches the poller itself. Each stayed alive for hours (one for 21 h) after the watched command finished, and the agents' turns ended "waiting" on them.

Fix: a PreToolUse Bash hook (`.claude/hooks/pgrep-self-match-guard.py`) that denies a Bash command containing `pgrep -f <literal>` (or `ps ... | grep <literal>` without the `[f]oo` bracket trick) and names the recipes that do not self-match: `pgrep -x`, a pattern assembled from a variable, the bracket trick, or waiting on the harness task notification / a `$!` pid. One override: `FROB_SELF_MATCH_ACK=1`. Materialized to `~/.claude/hooks/` via the `MANAGED` list and registered in the project settings.
