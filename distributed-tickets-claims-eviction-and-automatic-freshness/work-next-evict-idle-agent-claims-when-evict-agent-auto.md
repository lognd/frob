+++
id = "01M5DJW52ZBQRYN9ZSTGSJJYF3"
title = "work --next: evict idle agent claims when evict_agent = auto"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T21:18:28Z"
updated = "2026-10-20T23:22:56Z"
+++

found while working ~QEH8MRN. work --next skips lost claims but does not yet evict idle agent claims when evict_agent = "auto" (docs/design/distributed-tickets.md).
