+++
id = "01M35RZY7MEWNFG9P8JWACT55Y"
title = "SEO/WEBPERF substrate: per-route head metadata extraction"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0V388SVN54W7PX2ZBW"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5364"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_seo_substrate.py", "tests/fixtures/webapp/seo1xx/**", "docs/modules/webapp-seo.md", "tests/unit/test_webapp_seo_substrate.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Tree-sitter query over HTML/JSX for <head> contents (title, meta tags, link tags, JSON-LD script blocks) normalized into a PageMetadata model per route, reused by every SEO/WEBPERF rule below instead of re-querying the DOM each time. Also builds the route-table-wide duplicate-detection index. Fixture: multi-route fixture app with one duplicate-title pair planted.
