+++
id = "01M6Q8W24RCXCYWVVQB5JWHC8T"
title = "PM039: supply landed_design facts from frob-check host"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-06T01:51:46Z"
updated = "2026-11-06T01:51:46Z"
labels = ["no-story"]
scope = ["crates/frob-check/src/host.rs"]
+++

Found while working ~5JKQ2BP. PM039 is silent until a host implements PmHost::landed_design. The graph JSON has no bound identities and the host has no landed-diff identities yet. no-story: follow-up to the landed PM039 rule, no standalone user-visible story.
