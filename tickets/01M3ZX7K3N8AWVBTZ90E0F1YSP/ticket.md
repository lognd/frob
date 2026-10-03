+++
id = "01M3ZX7K3N8AWVBTZ90E0F1YSP"
title = "PACK001-PACK008 findings in grimble-capabilities"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:25Z"
updated = "2026-10-03T03:34:25Z"
idempotency_key = "m2-packs-rules"
labels = ["milestone:2", "area:packs"]
scope = ["crates/grimble-capabilities/src/pack_rules/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z714EEST9EGEHWWV56RXG4"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FTSKACE9TE7MBHQH7ET"

[[acceptance]]
text = "Given a changed pack item, when checked, then one PACK001 per item is emitted with reason changed, added, removed or lock-missing"
bound = false

[[acceptance]]
text = "Given an enabled pack that cannot be loaded, when checked, then PACK006 is a required Unresolved and PACK001 does not evaluate that pack"
bound = false
+++

Implements packs.md section 9; security.md section 4.

Implement the PACK family with polarity, needs and fire/clean/unresolved corpora; PACK006 gets its RequiredReason; PACK009 is retired and never reused.
