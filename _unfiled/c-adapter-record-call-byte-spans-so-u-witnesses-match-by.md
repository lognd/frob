+++
id = "01M7088KB2KPY8SSBAAA3J5A4Y"
title = "C# adapter: record call byte spans so U witnesses match by span"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T13:34:18Z"
updated = "2026-11-09T13:48:04Z"
scope = ["crates/gob-symbols/src/csharp.rs", "changelog.d/01M703GDA7AME8ZR6PJGM874K6.changed.md"]
+++

C# CallSite records only a line; add byte spans like java.rs and drop the line fallback for C# in grimble-check log/pass.rs. Follow-up of MV8PWVD.
