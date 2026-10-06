+++
id = "01M3ZX7HN0YF3SYGVJRT5H07H5"
title = "cargo dev gen rules: std GRL to generated Rust, GEN001, no ambient effects"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-06T13:56:21Z"
idempotency_key = "m2-codegen-gen"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-dev/src/**", "packs/std/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[links]]
kind = "blocked-by"
target = "01M3ZX7HGX4HXKW1X8VKHW9BKW"

[[acceptance]]
text = "Given a std GRL source changed without regeneration, when `cargo dev gen all --check` runs, then GEN001 reports the generated module"
bound = false

[[acceptance]]
text = "Given the generated module, when inspected, then it has #![forbid(unsafe_code)] and the model gives its node no grants so any ambient effect is CAP001"
bound = false
+++

Implements plugins.md section 6.1; security.md section 2.8.

Never build.rs. The generated module carries #![forbid(unsafe_code)] and a grimble node with no grants; GEN001 regenerates and byte-compares.
