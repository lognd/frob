+++
id = "01M35RZY8TCGS4TV75ZBRG0VTQ"
title = "Add EXPRESS to FrameworkKind and extend WEBSEC authz substrate to Express handlers"
type = "task"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5402"]
labels = ["milestone:v0.535.0", "v1-cluster:B2", "area:grimble"]
+++

T-5356 names Express in its body but frob.webapp._detect.FrameworkKind (T-5302) has no EXPRESS member, so the authz substrate skips Express handlers; documented in docs/modules/webapp-websec-authz.md. Add EXPRESS detection (package.json dependency 'express', app.get/post route shape) in _detect.py with positive/negative fixtures, then teach _websec_authz_substrate to scan Express route handlers for ORM lookups without a req.user/session reference. Scope: src/frob/webapp/_detect.py, src/frob/webapp/_websec_authz_substrate.py, tests/fixtures/webapp/{express,websec4xx/express}/**, tests/unit/test_webapp_detect.py, tests/unit/test_webapp_websec_authz_substrate.py.
