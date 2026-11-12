+++
id = "01M77S60NMH0N01DJ75WTNW65J"
title = "Remove the frob-lease -> frob-metrics layering violation (activity journal recording)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-12T11:44:40Z"
updated = "2026-11-12T14:15:39Z"
labels = ["no-story"]
scope = ["crates/frob-ledger/**", "crates/frob-metrics/**", "crates/frob-lease/**", "crates/gob-dev/tests/it/layering.rs", "Cargo.lock", "docs/design/frob/pm-and-releases.md", "changelog.d/01M77S60NMH0N01DJ75WTNW65J.changed.md"]

[[acceptance]]
text = "frob-lease no longer depends on frob-metrics; activity module lives in frob-ledger and is re-exported by frob-metrics"
bound = false

[[acceptance]]
text = "ALLOWED row for frob-lease -> frob-metrics deleted from crates/gob-dev/tests/it/layering.rs"
bound = false
+++
