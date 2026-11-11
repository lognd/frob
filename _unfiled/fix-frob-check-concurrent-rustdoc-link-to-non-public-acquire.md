+++
id = "01M75MXWWPNSXC7SGDAS35JA07"
title = "Fix frob-check concurrent rustdoc link to non-public acquire"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-11-11T15:51:51Z"
updated = "2026-11-11T15:52:05Z"
scope = ["crates/frob-check/src/concurrent.rs", "changelog.d/**"]

[[acceptance]]
text = "frob-check concurrent.rs live_holder doc no longer intra-doc-links the non-public acquire"
bound = true
+++
