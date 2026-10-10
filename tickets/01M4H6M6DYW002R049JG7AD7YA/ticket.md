+++
id = "01M4H6M6DYW002R049JG7AD7YA"
title = "Docs phase 1 leftovers: status header on the four leased design docs and the tickets.md section 6 citations in frob-lease"
type = "docs"
category = "todo"
priority = "medium"
points = 1
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T20:45:41Z"
updated = "2026-10-10T19:12:43Z"
scope = ["docs/design/README.md", "docs/design/tickets.md", "docs/design/cli.md", "docs/design/build-test-ci.md", "crates/frob-lease/src/config.rs", "crates/frob-lease/src/lib.rs", "docs/schemas/config.json", "docs/reference/config.md", "changelog.d/**", "docs/README.md", "docs/design/sibling-contract.md", "docs/reference/tool-stages.md", "docs/design/tool-binding.md"]

[[acceptance]]
text = "Given docs/design/README.md, tickets.md, cli.md and build-test-ci.md, when this lands, then each starts with the Status/Owner/Decisions/Audience block and docs/README.md lists them as current instead of current*"
bound = false

[[acceptance]]
text = "Given the doc comments in crates/frob-lease/src/config.rs and lib.rs and their generated copies docs/schemas/config.json and docs/reference/config.md, when this lands, then they cite tickets.md section 3 instead of the nonexistent section 6, and cargo dev gen --check is clean"
bound = false

[[acceptance]]
text = "Given ~CV286BH landed, when this lands, then docs/design/sibling-contract.md describes the sibling skip in check --ticket and land (inputs: config, packs lock, model roots, any code-language file; reported as a warning with a reason)"
bound = false

[[acceptance]]
text = "Given ~5S319B4 landed, when this lands, then docs/reference/tool-stages.md and docs/design/tool-binding.md describe the uv-run Unresolved-with-remedy behaviour and frob work's uv sync --frozen in new worktrees (with the UV_PROJECT_ENVIRONMENT skip)"
bound = false
+++

found while working ~EE8MASY: these files were leased by in-flight tickets (MQ1NM4Q, 76AS8XH, FP0SDK3, TSYTGDE, ZZQ6PA9) so phase 1 left them; docs/README.md marks the four docs current*. Do after those tickets land.
