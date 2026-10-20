+++
id = "01M45469WCRVG2QME1TSYAQNAM"
title = "cargo dev ci docs step fails: WheelInfo doc links to private WHEEL_INFO_PY"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-05T04:12:15Z"
updated = "2026-10-05T04:23:54Z"
scope = ["crates/gob-dev/src/wheel_smoke.rs"]

[[acceptance]]
text = "Given the gob-dev crate, when rustdoc runs with -D warnings (cargo dev ci --step docs), then it succeeds with no private-intra-doc-links error"
bound = true

[[acceptance]]
text = "Given the WheelInfo doc comment, when read, then WHEEL_INFO_PY is referenced in plain code formatting rather than an intra-doc link"
bound = true
+++

found while working ~ER9HRA2: on experimental the docs ci step fails with rustdoc::private-intra-doc-links at wheel_smoke.rs (doc of WheelInfo links to the private item WHEEL_INFO_PY). Use plain backticks or make the link target public.
