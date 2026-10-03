+++
id = "01M3ZX7JE252WBVE5DKMJK3JME"
title = "Plan cache for disk packs, keyed by tree digest and engine fingerprint"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-03T03:34:24Z"
idempotency_key = "m2-packs-plan-cache"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/plan_cache.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EKNE5Q0NB0DKCH77AZX"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FPXFVAXEF6QJCFZ0A54"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JACXBTB74QS6TX6YZZE"

[[acceptance]]
text = "Given a pack loaded twice, when the second run starts, then the plan is read from the cache and not recompiled, and the cache path is under the XDG cache directory"
bound = false

[[acceptance]]
text = "Given a cache entry with an invalid MAC, when loaded, then it is discarded and rebuilt"
bound = false
+++

Implements plugins.md section 6.1; security.md section 2.2.

A disk pack's GRL is compiled on first load and cached outside the work tree (this supersedes the in-tree .grimble/cache/plans path of plugins.md), authenticated with the machine MAC.
