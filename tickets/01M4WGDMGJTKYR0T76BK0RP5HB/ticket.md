+++
id = "01M4WGDMGJTKYR0T76BK0RP5HB"
title = "Fix red experimental baseline: frob-gh layer entry, hand-rolled temp-and-rename in gob-cache and frob-land"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "Claude"
created = "2026-10-14T06:08:30Z"
updated = "2026-10-14T12:03:51Z"
scope = ["crates/gob-dev/**", "crates/gob-fs/**", "crates/gob-cache/**", "crates/frob-land/**", "changelog.d/**"]

[[acceptance]]
text = "Given experimental, when cargo test -p gob-dev -p gob-fs runs, then all pass"
bound = true
+++

gob-dev layering test: layer table lacks frob-gh. gob-fs inventory test: gob-cache/src/lib.rs:308 hard_link and frob-land/src/lock.rs:417 rename are hand-rolled temp-and-rename; use gob_fs::write_atomic or an allowlisted helper. Blocks frob land of every ticket (E-EVIDENCE-MISSING).
