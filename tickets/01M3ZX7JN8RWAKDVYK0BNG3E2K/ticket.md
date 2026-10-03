+++
id = "01M3ZX7JN8RWAKDVYK0BNG3E2K"
title = "Typed hook registry: versions, priority with name tie-break, config_tables"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:25Z"
updated = "2026-10-03T03:34:25Z"
idempotency_key = "m2-packs-hooks"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/hooks/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[acceptance]]
text = "Given a pack implementing an unknown hook or a wrong signature, when loaded, then PACK005 states the exact reason"
bound = false

[[acceptance]]
text = "Given two packs with equal priority on one hook, when ordered, then the tie-break is by pack name and the order is identical on every run"
bound = false
+++

Implements plugins.md section 5.

The hook list (atoms, detect, templates, check_file, check_repo, fix, adapter.fold, config_tables) is the whole ABI; implementations are validated at load (unknown hook, wrong signature, missing capability is PACK005 with the exact reason); no wrapper hook in version 1.
