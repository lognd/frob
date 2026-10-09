+++
id = "01M4FDQXEST75DK0NHDH4P5H15"
title = "ticket fragment text starts with a 'frob: ' prefix in consumer repositories"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T04:11:34Z"
updated = "2026-10-09T04:11:34Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-release/**", "crates/frob/**", "changelog.d/**"]

[[acceptance]]
text = "Given a consumer repository, when frob ticket fragment runs, then the skeleton text has no product-name prefix unless the repository configures one"
bound = false
+++
