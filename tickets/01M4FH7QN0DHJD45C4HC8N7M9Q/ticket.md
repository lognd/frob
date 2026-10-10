+++
id = "01M4FH7QN0DHJD45C4HC8N7M9Q"
title = "frob check --only refuses sibling rule ids and families (COLOR001, COLOR) as neither a rule family nor a rule id"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T05:12:38Z"
updated = "2026-10-10T21:34:53Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-check/**", "crates/gob-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given crunk and grimble configured, when frob check --only COLOR001 or --only COLOR or --only SYS runs, then the sibling's rules are selected and other rules are skipped; an id unknown to every product is still refused"
bound = false
+++

logand.app-v2 F-542 (second half). The crunk rule coverage gap is the crunk rule tickets in flight; telemetry in the worktree is ~5SQT8RX.
