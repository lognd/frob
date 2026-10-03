+++
id = "01M3ZX887RZB82G8HR5JKQ2FER"
title = "Repository tour: templates, five stops, pinned examples in [tour]"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:47Z"
updated = "2026-10-03T03:34:47Z"
idempotency_key = "m2-nav-tour-templates"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/gen/tour.rs", "crates/frob-ledger/templates/tour/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[links]]
kind = "blocked-by"
target = "01M3ZX87KRP6G49GHANMAK5JA8"

[[acceptance]]
text = "Given a ledger with done tickets, an epic and a good-first ticket, when generated, then TOUR.md has the five stops and pins the most recently closed ticket with evidence and a land, the largest epic and the first good-first ticket by ULID"
bound = false

[[acceptance]]
text = "Given a pinned ticket later dropped, when reindexed, then it is replaced and a note reports the replacement"
bound = false
+++

Implements navigation.md section 5.

TOUR.md on the ticket branch: what lives where, an epic, the life of one ticket, the guarding rules, your turn. Examples are pinned deterministically at the first reindex and written to materialized [tour] knobs; a vanished example is replaced and reported as a note. Nothing is model-written.
