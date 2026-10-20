+++
id = "01M3Z712WWYRXPSWNVDXX6K71R"
title = "Bind zizmor and actionlint through frob check tool stages; adopt in this repository"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-02T21:40:59Z"
idempotency_key = "m2-toolbind"
labels = ["milestone:2"]
scope = ["crates/frob-check/**", "frob.toml", ".github/**", "docs/reference/**"]

[[acceptance]]
text = "Given this repository, when frob check runs with the two stages configured, then zizmor and actionlint findings appear under CI ids and a tool that is missing yields one Unresolved finding"
bound = true
+++

cicd.md section 3: [[check.tool]] parsers for zizmor --format json-v1 and actionlint -format json mapping to CI ids with the repository's runner labels passed through, schema-lag results as Unresolved, findings carrying frob exceptions and evidence; frob.toml of this repository gains both stages and CI runs them; docs regenerated.
