+++
id = "01M35RZY7TW2SBMFTWK7K43C6E"
title = "COMPLY117-122: sector-specific (HIPAA/GLBA/COPPA/FERPA, flag-gated)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0SQG76SMW1YB0QHQEG"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5370"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_comply_sector.py", "tests/fixtures/webapp/comply1xx/sector/**", "tests/unit/test_webapp_comply_sector.py", "docs/modules/webapp-comply-sector.md"]

[[links]]
kind = "blocked-by"
target = "01M35RZY7G8XERH19A18K7XX5Z"
+++

All applicability-flag-gated per the corpus (financial_institution=true, directed_to_children=true) -- ship as config-driven rules reading a [comply] table in frob.toml the repo opts into, never inferred. Fixture: frob.toml fixture with each flag set.
