+++
id = "01M5JVWWAHEE8MPEWR40VRSM3E"
title = "profile.toml lacks scenarios for crunk edit/export dtcg/extract-token/import dtcg/new/rename"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-22T22:32:22Z"
updated = "2026-10-22T23:15:13Z"
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "gob-dev profile_coverage test passes: every crunk leaf command has a scenario or skip reason"
bound = false
+++

found while working ~MQE4F44; pre-existing from in-flight crunk tickets
