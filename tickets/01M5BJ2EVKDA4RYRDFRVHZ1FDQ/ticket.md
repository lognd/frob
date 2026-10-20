+++
id = "01M5BJ2EVKDA4RYRDFRVHZ1FDQ"
title = "frob claude: sync tracked hooks/agents/skills into ~/.claude (sync, status, uninstall)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T02:25:58Z"
updated = "2026-10-20T02:25:58Z"
idempotency_key = "claude-sync-verb"
+++

Add a noun-group verb 'frob claude' (same shape as lease/ticket/cycle) with subverbs: 'sync' (copy a MANAGED manifest from the repo into ~/.claude behind a do-not-edit banner, atomic temp+rename, backup, idempotent; also registers hooks in settings.json), 'status' (read-only drift report, exit 1 on drift; also surfaced as a frob doctor line), 'uninstall' (reverse only frob-owned files and settings entries, leave user additions untouched). Repo is canonical; never sync home -> repo. Reuse the idempotent/reversible settings.json install machinery from ~KHCKTS3 (do not duplicate it). Stale-source guard: refuse to sync a file whose worktree copy is behind base. Manifest is declared in frob.toml, not hardcoded. Hard tests: empty home, pre-existing user hooks, user edits after sync, uninstall preserves them, double sync byte-identical, drift detection. Prior art: old Python 'frob claude sync' (notes/v1/ops-and-integrations.md 6.4). Docs under docs/ in the same change.
