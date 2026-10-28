+++
id = "01M627BCWT16JMFK5E667DNHNY"
title = "Zero EXC005 findings (unattested frob:accept TOOL002)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-28T21:41:08Z"
updated = "2026-10-28T22:56:18Z"
idempotency_key = "b755-exc005"
scope = ["crates/gob-plan/**"]

[[acceptance]]
text = "frob check reports zero EXC005 findings"
bound = false
+++

Split from ~B755NCR (mis-scoped to docs/design/docs.md). Attest via frob ack in .github workflows and crates/gob-plan; frob.lock changes.
