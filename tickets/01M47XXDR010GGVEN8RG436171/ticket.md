+++
id = "01M47XXDR010GGVEN8RG436171"
title = "clippy-windows fails on experimental: ci.rs check-step test calls the unix-only step_named helper"
type = "bug"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-06T06:20:09Z"
updated = "2026-10-06T06:20:09Z"
scope = ["crates/gob-dev/src/ci.rs", "changelog.d/**"]

[[acceptance]]
text = "cargo dev ci --step clippy-windows passes on experimental"
bound = false

[[acceptance]]
text = "the test still runs on unix"
bound = false
+++

Landed with ~MDZJQZQ: crates/gob-dev/src/ci.rs test check_step_builds_the_workspace_siblings_before_running_frob calls step_named, which is cfg(unix), but the test itself is not, so the Windows target fails to compile the test module (cargo dev ci step clippy-windows; seen by ~PVJ9SQM 2026-10-06). The check step is Linux-only, so gate the test the same way as its neighbours. Also make the clippy-windows step part of what the land check or evidence runs so this class cannot land again, or file that as a follow-up.
