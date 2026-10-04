+++
id = "01M35RZY7DN74RKZQ3373VSC2E"
title = "WEBSEC401-407: route-level authorization (admin routes, IDOR/BOLA, mass assignment, pagination)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0R72ZC7F5PSP0BC04T"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5357"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_authz_routes.py", "tests/fixtures/webapp/websec4xx/routes/**", "tests/unit/test_websec_authz_routes.py", "docs/modules/webapp-websec-authz-routes.md"]

[[links]]
kind = "blocked-by"
target = "01M35RZY7C8CWW43XSDV2FJGPV"
+++

Admin routes without the framework's auth decorator/middleware, front-end-only permission guards (React router-guard AST cross-referenced against the server route table), IDOR/BOLA (5144-1 substrate), mass assignment (request.json/params passed whole to create/update), field-level over-exposure, list-endpoint pagination -- this rule is the canonical owner of list-endpoint-pagination; T-5147-6 (WEBPERF) blocks on this leaf instead of reimplementing the pagination check. Per-user rate limiting on auth/expensive endpoints. Fixture per rule id.
