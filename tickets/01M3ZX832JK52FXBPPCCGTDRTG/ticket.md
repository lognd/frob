+++
id = "01M3ZX832JK52FXBPPCCGTDRTG"
title = "IssueProjection: the tracker-independent description of a ticket"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-03T03:34:42Z"
idempotency_key = "m2-mirror-projection"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ81430D3D5QSNCFM8QB0"

[[acceptance]]
text = "Given a ticket with acceptance, scope, evidence and a blocked-by link, when projected, then the sections and relations appear typed and the render digest is stable across runs"
bound = false

[[acceptance]]
text = "Given a `[mirror] exclude` match, when projected, then the field is absent and recorded in private"
bound = false
+++

Implements mirror.md section 2.1.

New crate. Fold the ledger into one typed IssueProjection per ticket: identity, title, ordered typed sections (summary, acceptance, scope, evidence, links, managed_notice), classification, state, relations, people, provenance with render digest, private.
