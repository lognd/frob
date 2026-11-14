+++
id = "01M7AV384XMSFRSFYHH7YKMM10"
title = "crunk parity: compare Chromium to solver output, not a fixed JSON"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:15:50Z"
updated = "2026-11-14T05:10:15Z"
labels = ["no-story"]
scope = ["crates/crunk-*/**"]

[[acceptance]]
text = "Parity test diffs real solver output against Chromium."
bound = false
+++

H3: the parity test compares to a hard-coded document. Do not make it a CI job (user ruling); fix the comparison and review the existing crunk-parity job against that ruling. Source: frob-audit-grimble-crunk.md (Opus audit).
