+++
id = "01M4FDQXEST75DK0NHDH4P5H15"
title = "ticket fragment text starts with a 'frob: ' prefix in consumer repositories"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T04:11:34Z"
updated = "2026-10-10T18:56:52Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-release/**", "crates/frob/**", "changelog.d/**", "docs/reference/changelog.md", "docs/reference/config.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given a consumer repository, when frob ticket fragment runs, then the skeleton text has no product-name prefix unless the repository configures one"
bound = true

[[acceptance]]
text = 'Given [release] fragment_prefix = "frob: " in frob.toml, when frob ticket fragment runs, then the skeleton text starts with that prefix'
bound = true
+++
