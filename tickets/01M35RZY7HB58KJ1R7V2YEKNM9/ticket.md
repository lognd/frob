+++
id = "01M35RZY7HB58KJ1R7V2YEKNM9"
title = "LAUNCH checklist: advisory-only convention items"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M2Y1SS0SQG76SMW1YB0QHQEG"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5361"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_launch_checklist.py", "tests/fixtures/webapp/launch1xx/**", "tests/unit/test_launch_checklist.py", "docs/modules/webapp-launch-checklist.md"]

[[links]]
kind = "blocked-by"
target = "01M336K75R26P8713BNHT2T12M"

[[links]]
kind = "blocked-by"
target = "01M35RZY7G8XERH19A18K7XX5Z"
+++

Team photo, case studies, FAQ count, thank-you page, sticky mobile CTA, response-time promise, analytics presence -- per the owner directive these NEVER error. Use WEBSUB-4's new advisory Severity tier (not a never-fail flag on warn). File-existence/text-search checks only, no gate-blocking output.
