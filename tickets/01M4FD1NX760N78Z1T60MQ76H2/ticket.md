+++
id = "01M4FD1NX760N78Z1T60MQ76H2"
title = "Test thresholds in v2: min unit cases and line/branch coverage percent per scope (v1 [testing]) as config-driven COV rules"
type = "story"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T03:59:25Z"
updated = "2026-10-09T03:59:25Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-obligations/**", "crates/frob-tests/**", "crates/gob-config/**", "changelog.d/**"]

[[acceptance]]
text = "Given a [coverage] threshold table and a coverage report under the threshold, when frob check runs, then a COV finding names the scope, measured and required values; with no report the finding is Unresolved"
bound = false
+++

Hullbreach platform used v1 [testing] thresholds; v2 has no equivalent.
