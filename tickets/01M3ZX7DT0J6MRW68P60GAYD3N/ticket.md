+++
id = "01M3ZX7DT0J6MRW68P60GAYD3N"
title = "Generate docs/reference/grl/catalog.md and embed the catalog in the binary"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-03T03:34:20Z"
idempotency_key = "m2-grl-catalog-docs"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-dev/src/render/**", "docs/reference/grl/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7DMYNTWB3AP04CDMAECH"

[[acceptance]]
text = "Given the catalog, when `cargo dev gen all` runs, then docs/reference/grl/catalog.md is written and `cargo dev gen all --check` exits 0"
bound = false

[[acceptance]]
text = "Given a catalog word added without regeneration, when `--check` runs, then GEN001 reports the stale page"
bound = false
+++

Implements grl-spec.md section 6; documentation.md section 3.

One source for the page, the compiler and the engine: cargo dev gen writes the catalog page; GEN001 keeps it current.
