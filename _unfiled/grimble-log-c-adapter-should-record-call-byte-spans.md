+++
id = "01M703GDJ132187FES7K76C4D1"
title = "Grimble LOG: C# adapter should record call byte spans"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-09T12:11:11Z"
updated = "2026-11-09T12:11:11Z"
scope = ["crates/gob-symbols/src/csharp.rs"]
+++

found while working ~MV8PWVD: C# calls have start=end=0, so the LOG cross-check falls back to line coverage
