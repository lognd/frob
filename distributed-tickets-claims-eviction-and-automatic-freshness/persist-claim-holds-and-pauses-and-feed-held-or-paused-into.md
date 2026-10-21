+++
id = "01M5DXB27626TW58PZC41AWFVY"
title = "Persist claim holds and pauses and feed held_or_paused into work --next eviction"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T00:21:23Z"
updated = "2026-10-21T01:15:18Z"
+++

work --next eviction passes held_or_paused=false because no hold/pause store is readable from frob-worktree; since_reclaim_secs likewise has no reclaim record. Follow-up of 8DKB004.
