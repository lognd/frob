+++
id = "01M7088KDE2BPXD1H0EB2XD2JS"
title = "Bash adapter: record command call sites so U witnesses LOG001 for Bash"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T13:34:18Z"
updated = "2026-11-09T13:52:31Z"
scope = ["crates/gob-symbols/src/shell.rs", "crates/grimble-check/src/log/universal.rs", "changelog.d/01M7088KDE2BPXD1H0EB2XD2JS.changed.md"]
+++

shell.rs records no CallSite; record command invocations with byte spans as java.rs does. Follow-up of MV8PWVD.
