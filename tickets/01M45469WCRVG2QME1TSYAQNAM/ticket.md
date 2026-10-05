+++
id = "01M45469WCRVG2QME1TSYAQNAM"
title = "cargo dev ci docs step fails: WheelInfo doc links to private WHEEL_INFO_PY"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-05T04:12:15Z"
updated = "2026-10-05T04:17:27Z"
scope = ["crates/gob-dev/src/wheel_smoke.rs"]
+++

found while working ~ER9HRA2: on experimental the docs ci step fails with rustdoc::private-intra-doc-links at wheel_smoke.rs (doc of WheelInfo links to the private item WHEEL_INFO_PY). Use plain backticks or make the link target public.
