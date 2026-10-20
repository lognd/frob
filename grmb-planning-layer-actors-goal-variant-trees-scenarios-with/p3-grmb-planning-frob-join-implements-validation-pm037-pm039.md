+++
id = "01M4FDBDC401KMNN4C12QTA3PK"
title = "P3 grmb planning: frob join (implements validation, PM037-PM039, design_bound guard, plan --from-design)"
type = "story"
category = "todo"
priority = "medium"
points = 8
parent = "01M4FDAD29CBF7S4EM2FKR5TXQ"
reporter = "lognd"
created = "2026-10-09T04:04:44Z"
updated = "2026-10-09T04:04:44Z"
labels = ["grimble"]
scope = ["crates/frob-pm/**", "crates/frob-ledger/**", "crates/frob-check/**", "crates/frob/**", "docs/design/cli.md", "docs/design/tickets.md", "docs/design/pm-enforcement.md", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4FDBBXG990QVX35HERF5VCQ"

[[acceptance]]
text = "Given the web example, when frob plan --from-design --apply runs twice, then the second run proposes no ticket and every created ticket carries implements design:<anchor>"
bound = false

[[acceptance]]
text = "Given a task that implements an impl whose status_hi is declared, when frob ticket close runs with outcome done, then the close is refused by design_bound with PM038 and a remedy"
bound = false

[[acceptance]]
text = "Given an obligation with no implementing ticket, when frob check runs, then PM037 is reported as Advisory on that anchor"
bound = false
+++

grmb-planning.md 10, row P3. implements design: validation for planning anchors against the graph export; overlay planned, in-progress, done and the test verdict; PM037-PM039 in frob-pm; close guard design_bound in the default close set; frob plan --from-design with --apply and --findings (goal to epic, scenario to story, impl to task, idempotency key = anchor, scope and acceptance seeded, requires to blocked-by).
