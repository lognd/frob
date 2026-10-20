+++
id = "01M35RZY7V5ZA2F3HFTGCQG42B"
title = "WEBPERF101-108: Core Web Vitals causes in markup"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0V388SVN54W7PX2ZBW"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5371"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_webperf_markup.py", "tests/fixtures/webapp/webperf1xx/markup/**", "tests/unit/test_webapp_webperf_markup.py", "docs/modules/webapp-webperf-markup.md"]

[[links]]
kind = "blocked-by"
target = "01M35RZY7MEWNFG9P8JWACT55Y"
+++

Image width/height for CLS, loading=lazy on offscreen img/iframe, srcset, font-display, defer/async on head scripts, bundle-budget config assertion (webpack/vite), source-maps-in-prod cross-refs T-5143-3, not duplicated. Tree-sitter query over HTML/JSX (5147-1 substrate). Fixture per rule id.
