+++
id = "01M3ZX851JW2KYRMCCK5RQKG5W"
title = "Marker v1: MAC over (repository node id, ULID, nonce), creation-revision-only trust, MIR003"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T05:51:55Z"
idempotency_key = "m2-mirror-markers"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/marker.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[links]]
kind = "blocked-by"
target = "01M4052R0DZK01W7K8EE77637T"

[[acceptance]]
text = "Given an issue created by another user carrying a valid-looking marker, when the mirror runs, then it is ignored and MIR003 is reported"
bound = false

[[acceptance]]
text = "Given a bot issue whose marker HMAC is wrong, when the mirror runs, then it is not adopted"
bound = false
+++

Implements mirror.md section 3.3 (marker format, trust) and security.md section 2.11.

Format `frob:v1 kid=<id> ulid=<ULID> nonce=<n> mac=<...>`; the MAC covers (repository node id, ULID, nonce) under key kid from the keyring (m2-mirror2-keyring). A marker counts only in the bot-authored creation revision of the issue body (first revision, author a mirror bot id by user id); markers in later revisions change nothing. Any other issue carrying a marker is MIR003 (Advisory) and ignored; a marker under an unknown kid on a bot issue is MIR001 marker-key-unknown, never a recreate.
