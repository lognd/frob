+++
id = "01M5BY28D120GDA00N4VANXQRD"
title = "Wire mirror identities: bot_ids as user ids in frob mirror recreate, tracker key alias on publish, ticket show by alias"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-20T05:55:34Z"
updated = "2026-10-28T12:56:03Z"
labels = ["no-story"]
scope = ["crates/frob/src/mirror_recreate_cmd.rs", "crates/frob/src/mirror_cmd.rs"]
+++

Follow-up of ~KYWR6WX: crates/frob-mirror/src/identity.rs exists (IdentityConfig, resolve_people, add_tracker_alias, resolve_reference) but the CLI still reads bot_ids as logins, and the ledger has no add-alias event.

no-story: internal engineering task in frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
