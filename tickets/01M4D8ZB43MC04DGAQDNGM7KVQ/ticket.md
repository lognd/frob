+++
id = "01M4D8ZB43MC04DGAQDNGM7KVQ"
title = "gob-check: cargo JSON diagnostics parser for rustc and clippy with the Rust id map"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T08:09:45Z"
updated = "2026-10-08T08:09:45Z"
scope = ["changelog.d/**", "crates/gob-check/**", "frob.toml"]

[[acceptance]]
text = "Given cargo clippy --message-format=json output, when the stage runs, then unused lints map to DEAD, too_many_arguments to NEAT002, the correctness group to LOGIC and unmapped lints to LINT with source_rule"
bound = false

[[acceptance]]
text = "Given this repository, when frob check runs, then the clippy finding count equals cargo clippy's"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md rows K02, K05, K08, K14, K23, K30, K39 (4.2 N02); notes/research/mining-report-2026-10-08.md 3.6 C02, C16, C17. The cargo clippy stage in frob.toml is pass/fail only today.
