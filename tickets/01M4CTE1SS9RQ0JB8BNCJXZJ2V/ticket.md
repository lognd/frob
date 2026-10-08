+++
id = "01M4CTE1SS9RQ0JB8BNCJXZJ2V"
title = "Layering test over cargo metadata with the boundaries.md layer table (audit M9)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:39Z"
updated = "2026-10-08T03:55:39Z"
scope = ["changelog.d/**", "crates/gob-dev/**", "docs/design/boundaries.md"]

[[acceptance]]
text = "Given a new dependency edge that goes up a layer, when the test runs, then it fails naming both crates and their layers"
bound = false

[[acceptance]]
text = "Given the allow list, when a listed violation is fixed, then the stale row fails the test"
bound = false
+++

notes/review/audit-2026-10-07.md M9. boundaries.md section 6 claims the layering is enforced over Cargo metadata; nothing enforces it. Violations today: gob-dev -> product crates (until the split), gob-ir/gob-rules order, frob-lease -> frob-release, gob-walk reads frob.toml. Allow-list current violations with ticket pointers so the test lands green and each fix removes a row.
