+++
id = "01M3ZAABA0DY25WGBZ8KDJD9BA"
title = "Design follow-ups from G03 and G04: sibling rename, packs keys, SIB and PACK registration, config rows"
type = "docs"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T22:03:53Z"
updated = "2026-10-02T22:08:55Z"
idempotency_key = "m2-docs-followups"
labels = ["milestone:2"]
scope = ["docs/design/**", "docs/schemas/sibling.json"]

[[acceptance]]
text = "Given the design set, when grepped for grimble.sibling, SIB001 and PACK001, then the old id is gone and both families appear in rules.md and boundaries.md with owners"
bound = false
+++

Apply the cross-document edits listed in docs/design/packs.md section 12 and sibling-contract.md section 11: rename the sibling schema id grimble.sibling/1 to gob.sibling/1 everywhere (schema file, contract, README rows, grimble-model.md 9.5); add the additive packs and packs_digest keys and the pack-unavailable reason code to sibling-contract.md and docs/schemas/sibling.json, re-validating the worked examples; register the SIB and PACK families with id ranges and owners in rules.md and boundaries.md 2.5; add the [packs] and grimble.toml pack tables and the sibling_timeout_secs knob to architecture.md section 6; state in cli.md section 2 whether failed, timeout and malformed sibling cases are required (proposed: yes, all five sibling_missing reasons are required).
