+++
id = "01M5BA1W8S9BW9Z47AV2ZKVEX0"
title = "Mirror recreate: read [mirror] repo/kid/bot_ids from FrobConfig instead of env vars"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T00:05:50Z"
updated = "2026-10-20T00:50:06Z"
scope = ["crates/frob/src/mirror_recreate_cmd.rs", "crates/frob/src/config.rs", "docs/reference/config.md", "docs/schemas/config.json", "docs/design/mirror.md"]

[[acceptance]]
text = "frob mirror recreate reads repo, kid and bot_ids from the [mirror] table of frob.toml (FrobConfig) instead of FROB_MIRROR_KID"
bound = true
+++

Follow-up to ~48DKBVB: gob_config::MirrorTable now exists; add it to FrobConfig and use it in mirror_recreate_cmd (kid, repo default, bot ids), regenerate docs/reference/config.md and docs/schemas/config.json via gob-dev gen all.
