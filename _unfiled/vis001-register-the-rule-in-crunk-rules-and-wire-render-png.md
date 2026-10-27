+++
id = "01M5HBHRPS50C0M7RJRCFF3C0J"
title = "VIS001: register the rule in crunk-rules and wire render/PNG decode and diff encode"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:27:26Z"
updated = "2026-10-27T02:58:39Z"
scope = ["crates/crunk-rules/**", "crates/crunk-gallery/**", "docs/reference/rules/**", "docs/crunk/rules/**"]
+++

Found while doing ~R149H7C: the pure comparison (crunk_gallery::visual) exists. Still needed: a VIS001 #[rule] declaration plus md in crunk-rules, [vis] thresholds in crunk.toml, PNG decode of design and build renders and PNG encode of the diff image at the diff path (needs a png dependency and the T2 renderer).
