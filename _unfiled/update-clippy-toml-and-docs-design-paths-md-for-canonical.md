+++
id = "01M55VA2V2Y5C1GWC665C931XE"
title = "Update clippy.toml and docs/design/paths.md for canonical living in gob-fs"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T21:11:58Z"
updated = "2026-11-02T11:56:50Z"
scope = ["docs/design/shared/architecture.md", "changelog.d/01M55VA2V2Y5C1GWC665C931XE.fixed.md"]

[[acceptance]]
text = "Given architecture.md section 3.1.3.1, when read, then it names gob_fs::canonical (defined in gob-fs path.rs) as the canonicalize wrapper"
bound = false
+++

found while working ~NF2ZMQG: canonical moved to gob-fs; gob_exec::canonical is a re-export.
