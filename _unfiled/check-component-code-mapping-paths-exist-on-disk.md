+++
id = "01M5H15J89N27F4C4CH719QDG4"
title = "Check component code-mapping paths exist on disk"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T05:26:00Z"
updated = "2026-11-12T05:54:02Z"
labels = ["no-story"]
scope = ["crates/crunk-rules/**", "changelog.d/01M5H15J89N27F4C4CH719QDG4.*", "docs/reference/rules/COMP007.md"]

[[acceptance]]
text = "Given a component whose code-mapping path does not exist on disk, when COMP007 runs, then it reports a finding naming the path"
bound = true
+++

Cut from ~D6TTN3F: COMP007 checks the mapping is present and non-blank, not that path exists.

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
