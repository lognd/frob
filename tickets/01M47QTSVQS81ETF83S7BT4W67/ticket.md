+++
id = "01M47QTSVQS81ETF83S7BT4W67"
title = "gob-mdtest: snapshot-diagnostics header writes an insta snapshot of the rendered diagnostics"
type = "story"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:33:59Z"
updated = "2026-10-06T06:51:39Z"
scope = ["crates/gob-mdtest/**"]

[[acceptance]]
text = "a corpus with the header produces and checks per-block snapshots"
bound = true

[[acceptance]]
text = "a changed rendering fails with an insta diff"
bound = true

[[acceptance]]
text = "FORMAT.md documents the header"
bound = true
+++

build-test-ci.md section 6, ty's mdtest snapshot-diagnostics. A suite header comment snapshot-diagnostics makes the harness render every finding of each block with the full text renderer (source excerpt, labels, help) and assert it with insta, one snapshot per block, beside the corpus. Document it in crates/gob-mdtest/FORMAT.md.
