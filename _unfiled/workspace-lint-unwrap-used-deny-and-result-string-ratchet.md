+++
id = "01M7EXR2Q2KQXVMKRWVDCW3NKY"
title = "workspace lint: unwrap_used deny and Result<_, String> ratchet"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:07Z"
updated = "2026-11-15T06:19:08Z"
labels = ["no-story"]

[[acceptance]]
text = "unwrap_used is denied outside tests"
bound = false
+++

Source: frob-audit2-repo.md L2. Evidence: no unwrap_used in Cargo.toml lints. Remedy: add lint with a ratchet baseline. Files: Cargo.toml.
