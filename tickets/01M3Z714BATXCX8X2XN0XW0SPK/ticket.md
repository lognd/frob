+++
id = "01M3Z714BATXCX8X2XN0XW0SPK"
title = "G13: frob orchestration of grimble as a sibling stage"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-03T01:23:20Z"
idempotency_key = "m2-orchestrate"
labels = ["milestone:2"]
scope = ["crates/frob-check/**", "crates/frob-obligations/**", "crates/frob-ledger/**", "crates/gob-check/**", "docs/reference/**", "docs/schemas/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712PSRGMHPGJ01CMBK6TR"

[[links]]
kind = "blocked-by"
target = "01M3Z713NBP986Q2ZDHKKR84AW"

[[links]]
kind = "blocked-by"
target = "01M3Z713YNM5666B7YFEHPFVKD"

[[acceptance]]
text = "Given grimble.toml present and no grimble binary, when frob check runs with the default knobs, then exit is 1 with one required Unresolved finding naming the product"
bound = true
+++

D28 and the sibling contract: frob check runs grimble check --json when grimble.toml exists, validates the schema version, evaluates ticket-bound exception exits, merges findings and fidelity, and fails the gate when the sibling is absent per fail_on_unresolved required.
