+++
id = "01M35RZY7WBVBZEP6AJPTSGQXT"
title = "COMPLY101-108: privacy-policy page content, CCPA/CalOPPA"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M2Y1SS0SQG76SMW1YB0QHQEG"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5372"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/webapp/_comply_privacy.py", "tests/fixtures/webapp/comply1xx/privacy/**", "tests/unit/test_webapp_comply_privacy.py", "docs/modules/webapp-comply-privacy.md", "src/frob/gates/_taint_gate.py"]

[[links]]
kind = "blocked-by"
target = "01M35RZY7G8XERH19A18K7XX5Z"
+++

Required /privacy page + text-search for 'categories collected'/'effective date'/'do not track' sections (CalOPPA 22575(b)), 12-month-staleness lint on a frontmatter last_updated date (CCPA 1798.130(a)(5)), Do-Not-Sell link presence when a tracking pixel is detected (CCPA 1798.135(a)). Markdown/HTML content lint (regex/text-search, no grammar needed). Fixture: compliant and non-compliant privacy-policy pages.
