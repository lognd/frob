+++
id = "01M47RDBED35TFDEHQ1YTG1ZYC"
title = "Surface BuildStats.malformed_projects as a check finding and Unresolved status"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T04:44:06Z"
updated = "2026-10-06T04:44:06Z"
scope = ["crates/gob-check/src"]
+++

found while working ~ECEBCQ1: gob-symbols now lists malformed .csproj and .sln files in BuildStats.malformed_projects (path, reason). gob-check must turn each into a finding naming the file and mark the project Unresolved, like READ001 for unreadable files.
