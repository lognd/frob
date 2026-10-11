+++
id = "01M4MH62ATTYVEF66Y4C93BJQC"
title = "Affected-only clippy and fmt: scope the {packages} placeholder to the touched crates plus their direct reverse dependencies from cargo metadata, not the transitive closure"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:47:55Z"
updated = "2026-10-11T04:25:32Z"
scope = ["crates/frob-check/**", "crates/gob-check/**", "docs/**"]

[[acceptance]]
text = "for a change confined to one leaf crate the clippy stage names only that crate and its direct dependents, and for a core crate it names the transitive closure only when the public API changed, covered by a test over a fixture workspace"
bound = true
+++

measured: a change to a core crate such as gob-ir expands {packages} to most of 43 crates, and clippy --all-targets over them dominates the 87 s of tool time.
