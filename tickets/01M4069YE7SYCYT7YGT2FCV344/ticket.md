+++
id = "01M4069YE7SYCYT7YGT2FCV344"
title = "0.532.0 release notes and v1 to v2 upgrade guide (pin 0.531.0)"
type = "docs"
category = "todo"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:59Z"
updated = "2026-10-03T06:13:13Z"
idempotency_key = "m2-rel-release-notes"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["docs/guides/upgrade-from-v1.md", "changelog.d/**"]

[[acceptance]]
text = "Given the guide, when read, then it contains the exact pin command for 0.531.0"
bound = false

[[acceptance]]
text = "Given the changelog compile, when run, then the v2 notice leads the 0.532.0 section"
bound = false
+++

States plainly that frob 0.532.0 is the v2 Rust rewrite and replaces v1 on upgrade, lists the v1 to v2 differences (migration.md), and gives exact pin commands: `uv tool install frob==0.531.0` and `pip install frob==0.531.0`. Included in the GitHub release body and PyPI long description.
