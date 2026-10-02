## Done report

gob-dev generator per documentation.md sections 2-3 and build-test-ci.md section 3: cargo dev gen rules|directives|config|cli|schemas|all [--check] [--root] over the inventories of gob-rules, gob-config, gob-directives, gob-cli, gob-diagnostics and the frob-cli lib target; rule pages embed mdtest fire and clean examples; deterministic sorted output with a generated header; --check prints unified diffs and exits 1 (GEN001 wired into CI); generated files committed under docs/reference and docs/schemas; determinism and no-orphan tests. Deviations: internal I/O errors exit 1 because gob-dev may not use std::process; docs/reference/cli/any.md documents the shared schema verb; paths follow the ticket brief rather than documentation.md's product-split table (reconcile in T-0029); no ticket schema until frob-ledger lands.

### Changed
```
 .github/workflows/ci.yml                |   2 +
 Cargo.lock                              |  13 ++
 crates/gob-dev/Cargo.toml               |  23 +++
 crates/gob-dev/src/files.rs             | 125 +++++++++++++++
 crates/gob-dev/src/lib.rs               |  86 ++++++++++
 crates/gob-dev/src/main.rs              |  74 +++++++--
 crates/gob-dev/src/out.rs               |  12 ++
 crates/gob-dev/src/render/cli.rs        |  56 +++++++
 crates/gob-dev/src/render/config.rs     |  52 ++++++
 crates/gob-dev/src/render/directives.rs |  66 ++++++++
 crates/gob-dev/src/render/mod.rs        |  31 ++++
 crates/gob-dev/src/render/rules.rs      | 272 ++++++++++++++++++++++++++++++++
 crates/gob-dev/src/render/schemas.rs    |  51 ++++++
 crates/gob-dev/tests/generate.rs        |  99 ++++++++++++
 docs/reference/cli/any.md               |   7 +
 docs/reference/cli/frob.md              |  10 ++
 docs/reference/config.md                |  48 ++++++
 docs/reference/directives.md            |  66 ++++++++
 docs/reference/rules/CFG001.md          |  19 +++
 docs/reference/rules/DSL001.md          |  60 +++++++
 docs/reference/rules/DSL002.md          |  66 ++++++++
 docs/reference/rules/PARSE001.md        | 129 +++++++++++++++
 docs/reference/rules/README.md          |  22 +++
 docs/schemas/config.json                |  80 ++++++++++
 docs/schemas/directives.json            | 169 ++++++++++++++++++++
 docs/schemas/envelope.json              | 152 ++++++++++++++++++
 tickets/T-0016/ticket.md                |   6 +-
 27 files changed, 1776 insertions(+), 20 deletions(-)
```

### Evidence
(no evidence recorded)
