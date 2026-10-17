+++
id = "01M55VDSD2GHYJMFSQWPR7WM45"
title = "frob check: flag to skip tool stages so CI does not run fmt/clippy/gen/zizmor/actionlint/deny/shear/typos twice (audit M18)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T21:13:59Z"
updated = "2026-10-17T23:36:29Z"
scope = ["crates/gob-dev/src/ci.rs", "docs/design/cli.md", "crates/frob-check/src/verb.rs"]

[[acceptance]]
text = "frob check accepts --skip-tools and skips the [[check.tool]] stages"
bound = true

[[acceptance]]
text = "the CI check step passes --skip-tools so no tool stage runs twice per OS"
bound = true
+++

found while working ~BN7DCP3: dedupe needs a CLI flag for skip_tools; then ci.rs sibling_check passes it
