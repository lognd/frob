+++
id = "01M5H5P5KF5WHTPQVJ4WM2DDBN"
title = "crunk: rule for duplicate content keys across files"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:44:59Z"
updated = "2026-11-12T06:53:27Z"
scope = ["crates/crunk-rules/**", "changelog.d/01M5H5P5KF5WHTPQVJ4WM2DDBN.*", "docs/reference/rules/CONTENT004.md", "docs/reference/rules/README.md", "docs/README.md"]

[[acceptance]]
text = "Given a content key defined in more than one design/content file, when CONTENT004 runs, then it reports a finding naming the key and the files that define it"
bound = true
+++

found while working ~VAAWD0R: duplicate_keys exists in content_files.rs but has no rule.
