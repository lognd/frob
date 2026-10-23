+++
id = "01M1T07J4AJY98HXJ2C563FZ0B"
title = "r19: --root flag + config-run locator line (A-092)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:03Z"
aliases = ["crunk:T-0138"]
labels = ["component:crunk", "source:crunk"]
scope = ["docs/design/02-specification.md", "docs/design/subsystems/shell.md", "docs/design/01-customer-requirements.md"]

[[acceptance]]
text = "given the three docs, when read, then the --root flag, the locator line, the unchanged cwd default, and CT/E2E ids are stated"
bound = true
+++

An agent ran check with a config inside the project from the worktree root and silently judged the wrong tree; only cd worked. The cwd default is the borrower contract and stays, but r19 exposes a --root flag beside --config on every pipeline command and every --config run prints a locator line naming the resolved spec path and root, so a wrong-root run is visible in its first line instead of silently wrong.
