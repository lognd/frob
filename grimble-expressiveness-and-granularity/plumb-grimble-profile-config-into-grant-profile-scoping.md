+++
id = "01M6QD4EKJ72F7J6CGQ9AK1STA"
title = "Plumb [grimble] profile config into grant profile scoping"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-06T03:06:15Z"
updated = "2026-11-06T03:25:33Z"
scope = ["crates/grimble-check/**"]
+++

Found while working ~CT14W34: a grant's profile=NAME scope is judged from the use's file path (tests/, *_test.*, test_*) or the GRIMBLE_PROFILE env var. Add a [grimble] profile config key and selector so the active profile comes from config, and pass it into caps::profile_of.
