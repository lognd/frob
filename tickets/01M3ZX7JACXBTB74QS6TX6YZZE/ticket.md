+++
id = "01M3ZX7JACXBTB74QS6TX6YZZE"
title = "Derived state outside the work tree with MAC and atomic writes"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-04T04:25:51Z"
idempotency_key = "m2-sec-state-dir"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/state/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[acceptance]]
text = "Given an entry with an invalid or missing MAC, when read, then it is discarded and rebuilt"
bound = false

[[acceptance]]
text = "Given `CI=true`, when a cache directory exists in the work tree, then it is ignored"
bound = false
+++

Implements security.md section 2.2 (I4).

Plans, compiled WASM, compiled grammars live under $XDG_CACHE_HOME/<product>/ keyed by tree digest and engine fingerprint, never by path; each entry carries a MAC; invalid entries are discarded and rebuilt; temp file plus rename and self-verify on read; CI mode (--base or CI=true) ignores any in-tree cache.
