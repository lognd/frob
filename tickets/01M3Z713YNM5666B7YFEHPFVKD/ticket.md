+++
id = "01M3Z713YNM5666B7YFEHPFVKD"
title = "G09: grimble binary skeleton: check --json, init, doctor, fmt, exceptions list"
type = "task"
category = "in-progress"
priority = "high"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-03T00:45:10Z"
idempotency_key = "m2-grimblebin"
labels = ["milestone:2"]
scope = ["crates/grimble/**", "crates/grimble-check/**", "crates/gob-cli/**", "crates/gob-exec/src/proc001.rs"]

[[links]]
kind = "blocked-by"
target = "01M3Z712PSRGMHPGJ01CMBK6TR"

[[links]]
kind = "blocked-by"
target = "01M3Z713NBP986Q2ZDHKKR84AW"

[[links]]
kind = "blocked-by"
target = "01M3Z713VGKF4Z0JJ3263XJMC3"

[[acceptance]]
text = "Given a repository with grimble.toml and no .grmb file, when grimble check --json runs, then a valid sibling document with zero findings and a fidelity report is produced"
bound = false
+++

boundaries.md and grimble-model.md 9.7: standalone grimble over gob-check with the sibling JSON schema (G03), grimble.toml with materialized knobs, doctor with fidelity report, fmt via grimble-model, exceptions list; no frob dependency.
