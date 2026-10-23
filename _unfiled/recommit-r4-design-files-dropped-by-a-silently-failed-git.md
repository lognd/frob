+++
id = "01M1QDTV18CRAGC50FR157968T"
title = "recommit r4 design files dropped by a silently failed git add"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:03Z"
aliases = ["crunk:T-0040"]
labels = ["component:crunk", "source:crunk"]
scope = [".gitignore", "docs/design/01-customer-requirements.md", "docs/design/03-system-design.md", "docs/design/05-components.md", "docs/design/subsystems/ingest.md", "docs/design/subsystems/values.md", "tickets/T-0038/ticket.md"]

[[acceptance]]
text = "given main HEAD, when git status runs, then no docs/design or .gitignore modifications remain unstaged and the r4 sections are present in HEAD"
bound = true
+++

The T-0031 commit captured only the two pre-staged new files; git add -A of the remaining 11 revised docs and .gitignore failed with stderr suppressed, leaving the r4 revision uncommitted on main. This ticket lands those exact files unchanged.
