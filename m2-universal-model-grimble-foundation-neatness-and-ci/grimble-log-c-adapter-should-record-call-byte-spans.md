+++
id = "01M703GDJ132187FES7K76C4D1"
title = "Grimble LOG: C# adapter should record call byte spans"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-11-09T12:11:11Z"
updated = "2026-11-12T12:36:38Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/csharp.rs"]
+++

found while working ~MV8PWVD: C# calls have start=end=0, so the LOG cross-check falls back to line coverage
