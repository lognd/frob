+++
id = "01M3ZX855DB35XQZQPFKYWR6WX"
title = "[mirror.identities] by tracker user id, [mirror] bot_ids, and tracker key as a ticket alias"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T05:51:55Z"
idempotency_key = "m2-mirror-identities"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/identity.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83XX6D2N7XDTVRVYV6TS"

[[links]]
kind = "blocked-by"
target = "01M4052R88Y0A9HQHDB86ERMEM"

[[acceptance]]
text = "Given an owner without a mapping, when published, then the issue is unassigned and the note says so"
bound = false

[[acceptance]]
text = "Given a published ticket, when `frob ticket show <tracker-key>` runs, then the ticket resolves"
bound = false
+++

Implements mirror.md sections 2.1 (people), 3.3 (own writes, bot ids) and 3.5 (identities by user id).

Identities are mapped by tracker user id, never login (logins can be released and claimed); [mirror] bot_ids lists the App identities by user id. Unmapped identities are left unassigned and noted; the tracker key becomes an alias so `frob ticket show PROJ-123` works.
