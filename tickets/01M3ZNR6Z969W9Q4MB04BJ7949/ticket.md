+++
id = "01M3ZNR6Z969W9Q4MB04BJ7949"
title = "Sibling follow-ups: materialized knobs, shared compute digest, state dirs never walked, grimble evidence, output cap"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T01:23:41Z"
updated = "2026-10-03T01:23:41Z"
idempotency_key = "m2-sibling-followups"
labels = ["milestone:2"]
scope = ["crates/gob-config/**", "crates/grimble-check/**", "crates/frob-check/**", "crates/gob-walk/**", "crates/gob-exec/**", "crates/gob-check/**", "frob.toml", "docs/reference/**", "docs/schemas/**", "Cargo.lock"]

[[acceptance]]
text = "Given this repository, when frob check runs grimble as a sibling, then no finding names a .frob or .grimble path, the compute digests are compared, and both sibling knobs are materialized in frob.toml"
bound = false
+++

From ~0XW0SPK and ~FRHX0KM: (1) mark [check] sibling_timeout_secs and require_siblings as enforcement knobs and materialize them in this repository's frob.toml; (2) move the canonical compute digest from grimble-check (ComputeTable::digest) into gob-config so frob compares the sibling's compute_digest for equality and refuses a mismatch as SIB001 incompatible; (3) gob-walk always skips tool state directories (.frob/, .grimble/, .git/) so grimble never reports frob's cache as unowned; (4) add grimble to [evidence] allowed_tools so grimble runs can be ticket evidence; (5) gob-exec enforces an output cap per spec (knob, default 64 MiB) instead of frob checking stdout length afterwards; (6) register crunk in the SIBLINGS table as not yet available (absent unless crunk.toml exists).
