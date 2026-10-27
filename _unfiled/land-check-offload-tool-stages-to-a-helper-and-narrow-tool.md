+++
id = "01M4W9XRMF6K8GPJCD23AX3CNZ"
title = "Land check: offload tool stages to a helper and narrow tool-memo inputs"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-14T04:14:59Z"
updated = "2026-10-27T02:58:19Z"
scope = ["crates/frob-land/**", "crates/gob-check/**", "crates/frob-check/**"]

[[acceptance]]
text = "An opt-in offload runs the scoped check's cargo stages on a helper with local fallback; the tool memo key covers only affected packages' files."
bound = false
+++

found while working ~NPGXR8M. Per-stage land timings now exist (stages in the land envelope). Left open: (1) opt-in offload of the scoped check's cargo tool stages to a helper via goway, falling back locally on exit 125, timeout or unparsable output; (2) the tool memo key hashes every file matching a stage's inputs globs, so repo-wide **/*.rs inputs make any base .rs change a memo miss on a stale-base retry; narrow keys to the affected packages' files.
