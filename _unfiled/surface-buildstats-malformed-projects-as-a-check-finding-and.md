+++
id = "01M47RDBED35TFDEHQ1YTG1ZYC"
title = "Surface BuildStats.malformed_projects as a check finding and Unresolved status"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-06T04:44:06Z"
updated = "2026-10-21T23:21:45Z"
scope = ["crates/gob-check/src", "crates/gob-check/src/product.rs", "crates/gob-check/src/pipeline.rs", "crates/gob-check/src/status.rs", "crates/gob-check/tests/pipeline.rs", "changelog.d/01M47RDBED35TFDEHQ1YTG1ZYC.added.md"]

[[acceptance]]
text = "Given a malformed .csproj or .sln, when gob-check runs, then a finding names the file and the project is marked Unresolved"
bound = true

[[acceptance]]
text = "Given several malformed projects (.csproj and .sln, duplicates, or already unreadable), when gob-check runs, then each file gets exactly one required Unresolved READ001 finding carrying its reason"
bound = true
+++

found while working ~ECEBCQ1: gob-symbols now lists malformed .csproj and .sln files in BuildStats.malformed_projects (path, reason). gob-check must turn each into a finding naming the file and mark the project Unresolved, like READ001 for unreadable files.
