+++
id = "01M35RZY7KWMKVSHM3YCRP0VPB"
title = "COMPLY123-127: subscription/cancellation/commerce dark patterns"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0SQG76SMW1YB0QHQEG"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5363"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_comply_commerce.py", "tests/fixtures/webapp/comply1xx/commerce/**", "tests/unit/test_webapp_comply_commerce.py", "docs/modules/webapp-comply-commerce.md"]

[[links]]
kind = "blocked-by"
target = "01M35RZY7G8XERH19A18K7XX5Z"
+++

16 CFR 425 click-to-cancel/equal-prominence cancel path, CAN-SPAM unsubscribe link + postal address in email templates, PCI SAQ-A scope check. Stripe webhook signature cross-refs T-5144-3, not duplicated. Route-table lint for subscribe/checkout without a comparable-depth cancel route; email-template regex/text-search. Fixture per rule id.
