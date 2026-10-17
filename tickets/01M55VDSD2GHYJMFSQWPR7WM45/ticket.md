+++
id = "01M55VDSD2GHYJMFSQWPR7WM45"
title = "frob check: flag to skip tool stages so CI does not run fmt/clippy/gen/zizmor/actionlint/deny/shear/typos twice (audit M18)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T21:13:59Z"
updated = "2026-10-17T23:29:00Z"
scope = ["crates/gob-dev/src/ci.rs", "docs/design/cli.md", "crates/frob-check/src/verb.rs"]
+++

found while working ~BN7DCP3: dedupe needs a CLI flag for skip_tools; then ci.rs sibling_check passes it
