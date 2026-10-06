+++
id = "01M43D7BB2BSB7XWCCZ13MJ53F"
title = "gob-macros::ui trybuild test takes 45-120 s and times out the 120 s hang guard on loaded hosts"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-04T12:11:38Z"
updated = "2026-10-06T04:43:37Z"
scope = ["crates/gob-macros/tests/**", "crates/gob-macros/Cargo.toml", ".config/nextest.toml"]

[[acceptance]]
text = "Given a loaded host (load average above the core count), when cargo dev ci runs, then gob-macros::ui finishes within the hang guard"
bound = false
+++

Several agents' cargo dev ci runs on 2026-10-04 timed out gob-macros::ui (a trybuild compile-fail test) at the 120 s nextest hang guard on loaded helpers; alone it takes 45-60 s. trybuild compiles every case in a fresh cargo project. Options: share the target dir with the workspace (CARGO_TARGET_DIR), split cases so they compile in one trybuild run, or give it a reviewed per-test override in .config/nextest.toml with a measured reason. Pick the structural one if it works.
