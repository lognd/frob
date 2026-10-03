+++
id = "01M3ZXGAS3HJR9NYAMKWYGETZK"
title = "Mirror reconcile: capture reverted edits from tracker history as proposal events"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:39:12Z"
updated = "2026-10-03T03:39:12Z"
idempotency_key = "m2-mirror-proposal-capture"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/**", "crates/frob-ledger/**"]

[[acceptance]]
text = "Given an edit made between the mirror's read and write, when the next run reads history, then the edit is recorded as a proposal and nothing is lost"
bound = false

[[acceptance]]
text = "Given ten edits by one unmapped user to one issue, when captured, then one collapsed proposal line results"
bound = false
+++

mirror.md 3.1. Read the tracker's change history since the last publish (GitHub timeline events: renamed, labeled, unlabeled, closed, reopened, assigned; body userContentEdits via GraphQL) and record each edit to a repository-owned field as a proposal event on the ticket (field, published value, tracker value, user, time, link), including edits that raced the mirror's write. Collapse repeated edits by one user to one field; collapse unmapped users per issue. Proposals never touch scope, acceptance, evidence or links. Fields without history are declared in adapter capabilities and captured at read time only.
