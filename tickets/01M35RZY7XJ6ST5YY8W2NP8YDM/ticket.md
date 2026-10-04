+++
id = "01M35RZY7XJ6ST5YY8W2NP8YDM"
title = "COMPLY109-116: GDPR/international disclosures"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M2Y1SS0SQG76SMW1YB0QHQEG"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5373"]
labels = ["milestone:0.534.0"]
scope = ["tests/fixtures/webapp/comply1xx/gdpr/**", "src/frob/webapp/_comply_gdpr.py", "tests/unit/test_comply_gdpr.py", "docs/modules/webapp-comply-gdpr.md"]

[[links]]
kind = "blocked-by"
target = "01M35RZY7G8XERH19A18K7XX5Z"
+++

DSAR SLA (GDPR Art.12(3), one month), Art.13 identity/legal-basis/retention text, right-to-erasure endpoint (Art.17), storage-limitation/TTL schema check (Art.5(1)(e)) -- reuses 5148-4's migration-scan helper for the PII-retention-TTL-column check rather than building a second migration parser -- encryption-at-rest config, breach-notification runbook presence, EU AI Act Art.50 chatbot-notice, CASL/TCPA consent capture. Fixture per rule id.
