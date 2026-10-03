+++
id = "01M3ZX7Z8X5KAY28W5761CRGKF"
title = "Escape other non-ASCII in text from packs, the tracker and the ledger (OWNER call)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:38Z"
updated = "2026-10-03T03:34:38Z"
idempotency_key = "m2-sec-escape-nonascii"
labels = ["milestone:2", "area:security", "needs-owner"]
scope = ["crates/gob-diagnostics/src/escape.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7YW7S3BJ72FPRQ85F72V"

[[links]]
kind = "blocked-by"
target = "01M3ZX7Z0EM0DCAHC59PJH50MJ"

[[acceptance]]
text = 'Given a pack message containing an accented letter, when rendered as text, then it appears as \u{e9}'
bound = false

[[acceptance]]
text = "Given the same character in a source snippet, when rendered, then it is shown as is"
bound = false
+++

Implements security.md sections 2.10 and 5 item 2.

Proposed policy: escape other non-ASCII as \u{...} only in pack, tracker and ledger text; show source snippets as they are. Awaiting owner confirmation; implement only after the call.
