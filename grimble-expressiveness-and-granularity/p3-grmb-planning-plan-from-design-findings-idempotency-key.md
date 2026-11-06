+++
id = "01M6PJTS38G6EGSH32FPD01BKM"
title = "P3 grmb planning: plan --from-design findings, idempotency key, seeding and blocked-by"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-05T19:26:35Z"
updated = "2026-11-06T00:34:26Z"
labels = ["no-story"]
scope = ["crates/frob/src/plan_cmd.rs", "crates/frob/src/plan/**", "docs/design/cli.md", "changelog.d/**", "crates/frob/tests/it/**"]

[[acceptance]]
text = "Given frob plan --from-design, when it proposes tickets, then idempotency key is the anchor, scope and acceptance are seeded, and requires maps to blocked-by"
bound = false

[[acceptance]]
text = "Given frob plan --from-design --findings, when anchors cannot be mapped, then they are listed"
bound = false
+++

Split from ~P9A8KME, which delivered the goal to epic, scenario to story, impl to task mapping with implements links and a no-op second --apply (idempotent via the live-ticket overlay, not keys).

Acceptance
1. [ ] Given frob plan --from-design, when it proposes tickets, then idempotency key is the anchor, scope and acceptance are seeded, and requires maps to blocked-by
2. [ ] Given frob plan --from-design --findings, when anchors cannot be mapped, then they are listed
no-story: follow-up to an already-landed story; no standalone user-visible story.
