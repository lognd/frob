+++
id = "01M3ZX7K7BN0CEADJFMCTGEA64"
title = "Repository pack loader for tiers 1 and 2"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:25Z"
updated = "2026-10-03T03:34:25Z"
idempotency_key = "m2-packs-repo-loader"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-packs/src/loader/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FPXFVAXEF6QJCFZ0A54"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FTSKACE9TE7MBHQH7ET"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JACXBTB74QS6TX6YZZE"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JE252WBVE5DKMJK3JME"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JRYNHG0BHJ3ZHC9450N"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JWHQZQHD66HV2SB0498"

[[acceptance]]
text = "Given packs/py-safety with tier-1 and tier-2 content, when loaded, then atoms and rules are registered with provenance repo:packs/py-safety and the lock is verified"
bound = false

[[acceptance]]
text = "Given a pack declaring tier-3 wasm, when loaded before trust exists, then its rules report Unresolved pack-unavailable with the reason"
bound = false
+++

Implements plugins.md section 2; security.md sections 2.1 and 2.2.

Loads packs/<name>/: reads each file once into memory (digest, compile and use share the buffer), refuses tier 3 until gob-trust and the sandbox land, drops nothing silently.
