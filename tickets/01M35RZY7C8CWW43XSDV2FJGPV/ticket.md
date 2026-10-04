+++
id = "01M35RZY7C8CWW43XSDV2FJGPV"
title = "WEBSEC authz substrate: route/handler ownership-check AST walker"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M2Y1SS0R72ZC7F5PSP0BC04T"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5356"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_authz_substrate.py", "tests/fixtures/webapp/websec4xx/**", "tests/unit/test_webapp_websec_authz_substrate.py", "docs/modules/webapp-websec-authz.md"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Per-framework route-table extraction (Flask/FastAPI/Express/Django/Rails route decorators/registrations) plus a body-AST walk for an ORM filter/where clause referencing the authenticated user id -- ships as a documented heuristic (current_user/request.user/g.user identifier present, correlated with the ORM lookup call), not a sound analysis, same posture as PERF008's loop-invariant-effect heuristic. Fixture: one handler with the owner filter (clean) and one without (planted finding) per framework.
