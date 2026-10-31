+++
id = "01M69N030XZ3F08ZN5JZMD06WA"
title = "CI ubuntu: gob-check ui_product trybuild fails on duplicate-rule-id stderr"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T18:54:19Z"
updated = "2026-10-31T18:54:26Z"
idempotency_key = "ci-ui-product-1031"
scope = ["crates/gob-check/**"]

[[acceptance]]
text = "ui_product trybuild passes on CI ubuntu (stderr snapshots match the runner toolchain)"
bound = false
+++

CI run 41221220516 rust ubuntu: ui_product FAILED (66s) after E0080 duplicate COV001/same-slug messages. See ~FB6FTR5 (rust-src dependence) and ~13MJ53F.
