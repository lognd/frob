+++
id = "01M5D9HSNXET77WP5553V6YHME"
title = "refresh --background and --quiet flags for the freshness hooks"
type = "task"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-20T18:35:32Z"
updated = "2026-10-21T03:15:15Z"
+++

The git hooks and agent session hook from ~195YEC4 call frob refresh --background --quiet and --quiet; refresh_cmd.rs has neither flag yet (needs ~EV5KK0X background_kick). Add them: --background detaches via background_kick and returns at once, --quiet suppresses output; exit codes per distributed-tickets.md 5.4. Hooks tolerate the failure meanwhile.
