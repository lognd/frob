+++
id = "01M336K76MQDNAVK9KJ7CHCP2F"
title = "WEBSEC326-334: logging, timeouts, resource limits"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0Q1MXMXDHZ5ZJAD3XB"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5332"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_logging_limits.py", "tests/fixtures/webapp/websec3xx/logging/**", "tests/unit/test_websec_logging_limits.py", "docs/modules/webapp-websec-logging-limits.md"]

[[links]]
kind = "blocked-by"
target = "01M336K76D807X6VTTB7V8QPT1"
+++

Auth-event audit logging (V16.3.1/V16.3.2), log metadata completeness + UTC timestamps, PII in logs (extends 5143-3's secret-pattern reuse with a PII field-name denylist), log-retention policy (config), outbound HTTP client timeout missing, request body size limit missing, server request timeout (config), GraphQL introspection/depth limit (config), least-functionality (debug/test routes in prod route table), outbound egress allowlist (config), client storage cleared on logout. WebSocket origin check is owned by T-5141-4, NOT this leaf -- cross-reference its rule id instead of reimplementing. Fixture per rule id.
