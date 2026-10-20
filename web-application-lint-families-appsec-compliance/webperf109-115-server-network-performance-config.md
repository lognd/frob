+++
id = "01M35RZY7P9KD64VEF7DA3TNDB"
title = "WEBPERF109-115: server/network performance config"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0V388SVN54W7PX2ZBW"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5366"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_webperf_server.py", "tests/fixtures/webapp/webperf1xx/server/**", "tests/unit/test_webperf_server.py", "docs/modules/webapp-webperf-server.md"]

[[links]]
kind = "blocked-by"
target = "01M35RZY7MEWNFG9P8JWACT55Y"
+++

Compression middleware config, server cache layer for repeated expensive queries, undebounced-input-handler/unbounded-re-render React lint (hook dependency-array absence, onChange with no debounce). Cache-Control-on-hashed-assets is owned by T-5143-2, pagination-on-list-endpoints is owned by T-5144-2, and DB-pool-config is owned by T-5148-4 -- this leaf blocks on all three instead of reimplementing any of them. Fixture per rule id.
