+++
id = "01M5XNNK3SDJVM9ZYSYWJH6HZ7"
title = "Grimble capability docs: remove claims the code does not deliver"
type = "docs"
category = "todo"
priority = "medium"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:10Z"
updated = "2026-10-27T03:15:10Z"
idempotency_key = "grimble-expr-docs-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["docs/design/grimble-model.md", "docs/design/grmb-spec.md", "docs/guides/grimble.md", "docs/grimble/packs/grimble-websec.md", "docs/design/packs.md", "crates/grimble-bind/src/grants.rs"]

[[acceptance]]
text = "every capability claim in the listed docs is either true of the code or explicitly marked planned with a ticket id"
bound = false

[[acceptance]]
text = "the guide warns that may arguments and symbol at are not yet enforced (until the args and symat tickets land)"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. Until the implementation tickets land, the docs over-promise: docs/guides/grimble.md:195 recommends argument-scoped grants that are not enforced; grmb-spec.md 4.1 shows a symbol-scoped at; grimble-model.md 4 says detectors are 'typed call-site detectors (queries over U plus resolved callee)' and 9.6 says one vocabulary table and per-node Unresolved for unknown languages; grimble-model.md:43-44 and :123 still use the removed colon form and 'of CONSTRAINT'; grimble-websec.md:51 says net and db.query come from core-effects (they are MDL016); packs.md:206 promises MDL009 for wrongly typed args; grants.rs:357 says an argument-scoped grant is 'narrow by construction'. Mark each as planned with the ticket id, or fix the text.
