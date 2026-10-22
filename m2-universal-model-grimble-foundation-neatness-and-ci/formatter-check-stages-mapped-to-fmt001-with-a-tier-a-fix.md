+++
id = "01M4D94J5J2TZEXTB8GH36992B"
title = "Formatter check stages mapped to FMT001 with a tier A fix that runs the formatter within the ticket scope"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T08:12:36Z"
updated = "2026-10-22T13:41:07Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/frob/**", "docs/reference/tool-stages.md", "docs/schemas/config.json", "docs/reference/**"]

[[acceptance]]
text = "Given rustfmt, ruff format, prettier and dotnet format in check mode reporting a file, when frob check runs, then one FMT001 per file is reported"
bound = true

[[acceptance]]
text = "Given frob check --fix --ticket, when it runs, then only files inside the ticket scope are rewritten"
bound = true
+++

notes/research/lint-catalogue-2026-10-08.md row K27 (4.2 N07): notes/research/mining-report-2026-10-08.md C12 2.7 percent, 67 percent marked nit; notes/research/creators-systems-2026-10-08.md ADV017, ADV026 (automate formatting, do not discuss it). Check docs/migration/rule-ids.md: v1 FMT001/FMT002 were folded into PARSE.
