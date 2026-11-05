+++
id = "01M6BYKXB7YC4QSSW6XD4WAD09"
title = "P3 grmb planning: design_bound close guard (PM038) in the default close set"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4FDBDC401KMNN4C12QTA3PK"
reporter = "lognd"
created = "2026-11-01T16:20:54Z"
updated = "2026-11-05T19:29:16Z"
labels = ["grimble", "no-story"]
scope = ["crates/frob-ledger/src/guards.rs", "crates/frob-ledger/tests/**", "docs/design/tickets.md", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M6BYKR4XHDEJVRDYN5952RXW"

[[acceptance]]
text = "Given a task that implements an impl whose status_hi is declared, when frob ticket close runs with outcome done, then the close is refused by design_bound with PM038 and a remedy (parent AC2)"
bound = true
+++

Child of ~2QTA3PK. design_bound guard joins the default close set. Work no-story.
