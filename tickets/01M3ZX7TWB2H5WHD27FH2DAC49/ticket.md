+++
id = "01M3ZX7TWB2H5WHD27FH2DAC49"
title = "Relocate findings and plan caches out of the work tree under the MAC store"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:33Z"
updated = "2026-10-03T05:44:46Z"
idempotency_key = "m2-sec-cache-relocate"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-cache/src/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7JACXBTB74QS6TX6YZZE"

[[acceptance]]
text = "Given a warm cache, when a fresh process runs check, then findings come from the XDG store and the timing budget of D30 still holds"
bound = false

[[acceptance]]
text = "Given a forged findings row placed in the old in-tree location, when check runs, then it is never read"
bound = false
+++

Implements security.md section 2.2; conflicts with architecture.md D30 and D38 (see ticket body).

The landed per-worktree .frob/cache.sqlite is decision-bearing state in a place the repository can write. Move the cache default under $XDG_CACHE_HOME with authenticated entries, or record why the in-tree findings cache is acceptable. The conflict with D30 and D38 is listed in the planning report.
