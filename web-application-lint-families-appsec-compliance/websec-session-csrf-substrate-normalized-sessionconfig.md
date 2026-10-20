+++
id = "01M336K775CA7W9WDYAD339SEK"
title = "WEBSEC session/CSRF substrate: normalized SessionConfig reader"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0PCVWFZPFZT8VQ159Z"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5349"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_websec_session_config.py", "tests/fixtures/webapp/websec2xx/**", "docs/modules/webapp-websec-session.md", "tests/unit/test_webapp_websec_session_config.py", "design/frob.strata"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Framework-specific config-file parse (Django settings.py AST for MIDDLEWARE/SESSION_COOKIE_*; Flask app-factory AST for SESSION_COOKIE_*/app.config[...]; Express app.use(session(...)) call-argument AST; Rails config/initializers/session_store.rb + protect_from_forgery AST) producing one normalized SessionConfig model (secure/httponly/samesite/csrf_middleware_present/idle_timeout/absolute_timeout) every rule below reads instead of re-parsing. Fixture: one config fixture per framework, compliant and violating variants.
