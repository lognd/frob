+++
id = "01M4SMTYQMV149GQ3XQHJ87MVJ"
title = "Wire [release] registry_setup into release status and frob.toml"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-13T03:27:58Z"
updated = "2026-10-27T02:58:18Z"
scope = ["crates/frob/src/release_cmd.rs", "frob.toml"]
+++

found while working ~57AZHYH: frob-release has assess_with(input, registry_setup) and ReleaseConfig.registry_setup; release_cmd.rs must call assess_with(&input, cfg.release.registry_setup) and frob.toml set registry_setup = true, else frob loses its own registry-setup item.
