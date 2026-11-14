+++
id = "01M703GDJ132187FES7K76C4D1"
title = "Grimble LOG: C# adapter should record call byte spans"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-11-09T12:11:11Z"
updated = "2026-11-14T21:13:37Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/csharp.rs"]

[[acceptance]]
text = "C# call sites carry non-empty byte spans covering the call expression text"
bound = false
+++

found while working ~MV8PWVD: C# calls have start=end=0, so the LOG cross-check falls back to line coverage
