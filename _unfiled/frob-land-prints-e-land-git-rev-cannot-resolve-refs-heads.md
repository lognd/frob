+++
id = "01M4M27EDCXBRN2HZJXHAZK0F1"
title = "frob land prints E-LAND-GIT-REV (cannot resolve refs/heads/experimental) after a land that completed"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-10T23:26:32Z"
updated = "2026-10-10T23:26:32Z"
scope = ["crates/frob-land/src/**"]

[[acceptance]]
text = "a successful land of a ticket exits 0 with no error line, covered by a test that lands twice concurrently and once after the worktree is removed"
bound = false
+++

found while draining tickets: after a land had gone through (merge and close commits present, worktree removed, ticket done) the verb printed E-LAND-GIT-REV and exited non-zero. Seen when two landers raced; cause not identified.
