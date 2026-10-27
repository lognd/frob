+++
id = "01M1T07J473143TCEJC43SWK3F"
title = "r18: shell honesty batch (A-084..A-088)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:42Z"
aliases = ["crunk:T-0135"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/02-specification.md", "docs/design/subsystems/cache.md", "docs/design/subsystems/shell.md", "docs/design/subsystems/query.md", "docs/design/subsystems/report.md", "docs/design/01-customer-requirements.md"]

[[acceptance]]
text = "given the six docs, when read, then all five behaviors, the cache command surface, the marker file, and CT/E2E ids are stated"
bound = true
+++

Five field findings from the r17 battery: a path argument outside the project root tracebacks; a missing spec prints ERROR but exits 0 so a wrong-directory CI step passes silently; explain prints an empty closest clause; the cache home accumulates a store per ephemeral worktree root with no way to list or prune; an all-empty map inventory reads like a parse failure. r18: located outside-root diagnostic exit 2; missing spec exits 2 on every path; closest clause omitted when no candidate; a root marker file in each store plus an crunk cache subcommand (ls, prune by age or all) and opportunistic best-effort pruning of long-untouched stores on write; map prints an honest no-matching-files note naming css_root and the org model when every bucket is empty.
