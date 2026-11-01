+++
id = "01M6BFJGKXT2JXSB5TARP9EDXC"
title = "Embed a build id in sibling documents and --version so a stale same-version binary is detected"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:58:00Z"
updated = "2026-11-01T12:41:30Z"
scope = ["crates/frob-check/src/sibling/**", "crates/gob-check/build.rs", "crates/gob-check/src/build_id.rs", "crates/gob-check/src/sibling.rs", "crates/gob-check/src/sibling_doc.rs", "crates/gob-check/Cargo.toml", "crates/gob-check/src/lib.rs", "crates/gob-product/src/lib.rs"]

[[acceptance]]
text = "sibling document carries a build id and frob check warns when it differs from frob's, even at equal version"
bound = false
+++

Found by ~8P8875B: version-equality warning misses a stale binary built at the same version number.
