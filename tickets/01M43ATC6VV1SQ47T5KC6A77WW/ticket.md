+++
id = "01M43ATC6VV1SQ47T5KC6A77WW"
title = "Move LAYER and ORG rules to GRL in a crunk-core std pack"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:35Z"
updated = "2026-10-04T11:29:35Z"
idempotency_key = "crunk-plan-rgrl"
labels = ["area:crunk"]
scope = ["packs/crunk-core/**", "crates/crunk-rules/src/layers/**", "crates/crunk-rules/src/org/**", "crates/crunk-rules/Cargo.toml"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7ETPH5Z6K2VJ64K5XTMX"

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[links]]
kind = "blocked-by"
target = "01M3ZX7HN0YF3SYGVJRT5H07H5"

[[links]]
kind = "blocked-by"
target = "01M43ATBPPR5QCY0CSPPTNEDQ0"

[[acceptance]]
text = "Given the GRL rules, when the std pack builds, then findings equal the removed Rust rules on the corpus"
bound = false

[[acceptance]]
text = "Given the conformance test, when it runs, then compiled and plan findings are byte identical"
bound = false

[[acceptance]]
text = "Given a rule left in Rust, when the manifest is read, then the exception names the missing GRL construct"
bound = false
+++

plugins.md section 4 and 6.1: write LAYER001 and ORG001-005 in GRL with config.layers and config.org side relations typed from docs/schemas/crunk.json, compile into the binary through cargo dev gen rules, delete the Rust, and pass the conformance test (compiled equals plan, ~973VQTH). If a rule cannot be expressed, keep the Rust and record it as the exception in the pack manifest with the missing construct named (feeds owner decision on value-domain predicates).
