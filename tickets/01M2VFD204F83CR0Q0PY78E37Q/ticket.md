+++
id = "01M2VFD204F83CR0Q0PY78E37Q"
title = "frob-suggest: dedupe dual hook registration and make attempt counter per-agent-session"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-5124"]
scope = [".claude/settings.json", "tests/test_hook_frob_suggest.py", "tests/test_hook_sync_claude_config.py", ".claude/hooks/sync-claude-config.py", ".claude/hooks/frob-suggest.py", ".claude/hooks/_shellscan.py"]

[[acceptance]]
text = "sync-claude-config.py does not materialize a second registration of a hook the project settings.json already registers for the same repo, deduped by hook basename+event"
bound = false

[[acceptance]]
text = "attempt counter is keyed per FROB_AGENT/session id (falling back to parent pid), not per command-shape machine-global"
bound = false

[[acceptance]]
text = "a single Bash call increments the attempt count exactly once, proven by a test"
bound = false

[[acceptance]]
text = "O_EXCL denial dedupe is preserved"
bound = false
+++

Leaf 1 of T-draft-8c7e665d. See scratchpad/HOOK-AUDIT.md section 0b.
