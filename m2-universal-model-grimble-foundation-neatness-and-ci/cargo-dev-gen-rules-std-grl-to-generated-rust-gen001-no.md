+++
id = "01M3ZX7HN0YF3SYGVJRT5H07H5"
title = "cargo dev gen rules: std GRL to generated Rust, GEN001, no ambient effects"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-14T21:40:44Z"
idempotency_key = "m2-codegen-gen"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-dev/src/**", "packs/std/**", "design/model.grmb", "docs/reference/**", "crates/gob-plan/src/lower/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7HGX4HXKW1X8VKHW9BKW"

[[acceptance]]
text = "Given a std GRL source changed without regeneration, when `cargo dev gen all --check` runs, then GEN001 reports the generated module"
bound = true

[[acceptance]]
text = "Given the generated module, when inspected, then it has #![forbid(unsafe_code)] and the model gives its node no grants so any ambient effect is CAP001"
bound = true
+++

Implements plugins.md section 6.1; security.md section 2.8.

Never build.rs. The generated module carries #![forbid(unsafe_code)] and a grimble node with no grants; GEN001 regenerates and byte-compares.
