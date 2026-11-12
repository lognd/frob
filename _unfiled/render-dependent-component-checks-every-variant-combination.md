+++
id = "01M5H15HXSYYTSXC0ERNT1JMSB"
title = "Render-dependent component checks: every variant combination renders"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T05:26:00Z"
updated = "2026-11-12T09:53:50Z"
labels = ["no-story"]
scope = ["crates/crunk-rules/**", "changelog.d/*", "docs/reference/rules/COMP002.md", "changelog.d/01M5H15HXSYYTSXC0ERNT1JMSB.added.md"]

[[acceptance]]
text = "Given a component spec with a variant matrix, when COMP002 runs, then every variant combination is rendered and a combination that fails to render is reported"
bound = true
+++

Cut from ~D6TTN3F: COMP002 checks the matrix statically only; add render coverage of each variant cell.

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
