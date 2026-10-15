+++
id = "01M4Z6VV86D7XE2FSFF9AA532R"
title = "Fix unfulfilled clippy expectation in frob-tests typescript on windows"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-15T07:19:13Z"
updated = "2026-10-15T07:39:11Z"
idempotency_key = "fix-ts-expect-win"
scope = ["crates/frob-tests/tests/typescript.rs"]

[[acceptance]]
text = "clippy passes on windows target"
bound = true
+++

typescript.rs expect(clippy::disallowed_methods) is unfulfilled on windows because the display() call is unix-gated; use cfg_attr(unix, expect(...)).
