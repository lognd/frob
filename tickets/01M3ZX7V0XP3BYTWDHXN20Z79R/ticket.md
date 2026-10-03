+++
id = "01M3ZX7V0XP3BYTWDHXN20Z79R"
title = "Trust store: MAC'd entries, repository identity, expiry, list and revoke"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:33Z"
updated = "2026-10-03T03:34:33Z"
idempotency_key = "m2-sec-trust-store"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/store/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FPXFVAXEF6QJCFZ0A54"

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[acceptance]]
text = "Given an entry whose root commit differs from the repository, when consulted, then it does not match; given a hand-added unMAC'd line, then it is inert"
bound = false

[[acceptance]]
text = "Given an expired entry, when consulted, then it is untrusted and `doctor` reports it"
bound = false
+++

Implements security.md section 2.3 (The store).

$XDG_CONFIG_HOME/gob/trust.toml; identity is canonical root path plus root commit id plus remote URL (all must match); entries record who, when and expiry (90 days, 180 for network grants); trust list, trust revoke; doctor reports expired entries and a group- or world-writable store.
