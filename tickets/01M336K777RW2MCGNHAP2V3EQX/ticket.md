+++
id = "01M336K777RW2MCGNHAP2V3EQX"
title = "WEBSEC201-208: CSRF and session lifecycle"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0PCVWFZPFZT8VQ159Z"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5351"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_csrf_session.py", "tests/fixtures/webapp/websec2xx/csrf_session/**", "tests/unit/test_websec_csrf_session.py", "docs/modules/webapp-websec-csrf-session.md"]

[[links]]
kind = "blocked-by"
target = "01M336K775CA7W9WDYAD339SEK"
+++

State-changing GET requests, missing CSRF middleware, SameSite cookie default, client-only session-validity check, no session-id rotation on login, idle timeout config, absolute session lifetime config, logout server-side invalidation, plus the static half of account-enumeration-via-error-text. Route-table AST lint for the handler-shape rules, SessionConfig (5142-1) for the config rules. Fixture per rule id.
