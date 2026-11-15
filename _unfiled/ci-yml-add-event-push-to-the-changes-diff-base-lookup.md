+++
id = "01M7EX860A6WC3604BD3V727BH"
title = "ci.yml: add --event push to the changes diff base lookup"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:26Z"
updated = "2026-11-15T06:10:26Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md L9. Evidence: .github/workflows/ci.yml:78 selects a base run without filtering on event. Remedy: add --event push. Files: .github/workflows/ci.yml.
