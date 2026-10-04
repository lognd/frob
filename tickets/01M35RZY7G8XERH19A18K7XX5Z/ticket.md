+++
id = "01M35RZY7G8XERH19A18K7XX5Z"
title = "COMPLY substrate: required-page and site-signal detector"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M2Y1SS0SQG76SMW1YB0QHQEG"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5360"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_comply_substrate.py", "tests/fixtures/webapp/comply1xx/**", "docs/modules/webapp-comply.md", "tests/unit/test_webapp_comply_substrate.py"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Repo-behavior-signal detector: does this repo collect email/use AI on user data/have subscriptions/sell-or-share data/send SMS/embed session-replay-or-pixel/process health data, via manifest+import scan (package.json deps for stripe/twilio/fullstory/hotjar/openai, Python deps similarly) -- drives which COMPLY rules are relevant, mirrors WEBSUB-2's framework detection. Plus a route/sitemap scan for /privacy, /terms, /accessibility page presence keyed off the detected framework's router. Fixture: one repo fixture per signal plus a plain fixture with none.
