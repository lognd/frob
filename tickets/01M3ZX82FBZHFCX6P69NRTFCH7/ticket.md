+++
id = "01M3ZX82FBZHFCX6P69NRTFCH7"
title = "Ticket slug function"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:41Z"
updated = "2026-10-03T03:34:41Z"
idempotency_key = "m2-nav-slug"
labels = ["milestone:2", "area:navigation", "good-first"]
scope = ["crates/frob-ledger/src/slug.rs"]

[[acceptance]]
text = "Given the title `Parser rewrite: faster, safer (v2)!`, when slugged, then the result is `parser-rewrite-faster-safer-v2`"
bound = false

[[acceptance]]
text = "Given a title of only symbols or a 90-character title, when slugged, then the first yields the handle without the tilde and the second is cut at a word boundary within 60 characters"
bound = false
+++

Implements navigation.md section 2.1 (slug rules).

Pure function: title transliterated to ASCII, lowercased, runs of other characters become one dash, trimmed, cut at 60 characters on a word boundary; empty result becomes the handle without the tilde.

## Start here
Read navigation.md section 2.1 and crates/frob-ledger/src/id.rs for the handle type. Test: `cargo nextest run -p frob-ledger`. Ask: the repository owner (Logan) in a comment on this ticket.
