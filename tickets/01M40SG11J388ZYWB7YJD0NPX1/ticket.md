+++
id = "01M40SG11J388ZYWB7YJD0NPX1"
title = "frob init registers the merge driver as bare 'frob', which may resolve to a different frob on PATH"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T11:48:22Z"
updated = "2026-10-03T12:05:36Z"
idempotency_key = "m2-rel-init-driver-binary"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob/src/init.rs", "crates/frob/src/doctor*", "crates/frob/tests/**", "docs/design/cli.md", "changelog.d/01M40SG11J388ZYWB7YJD0NPX1.*"]

[[acceptance]]
text = "Given a different frob earlier on PATH, when frob init runs, then the driver command names the running executable's absolute path and the output says why"
bound = true

[[acceptance]]
text = "Given a driver command resolving to a different frob, when frob doctor runs, then it reports it with the fix"
bound = true
+++

Found on ~5Y8JFGW: frob init writes merge.frob-ledger.driver = 'frob merge-driver %O %A %B %P'. On a machine where 'frob' on PATH is another frob (here v1 0.531.1 from ~/.local/bin, while v2 runs from a build path), git would run the wrong binary on ledger files during a merge, risking corrupted or lost ledger data. The coordinator pinned this repository's config to the v2 binary by hand. Fix: init resolves 'frob' on PATH and compares it with the running executable (path and version); if they differ, it writes the running executable's absolute path into the driver command and says so (with a --driver-command override), and doctor reports a driver command that resolves to a different frob than the running one. Test both cases.
