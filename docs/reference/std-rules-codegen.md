# Std rule codegen

Status: current
Owner: gob
Decisions: none

`cargo dev gen std-rules` compiles each rule in `packs/std/rules/*.grl` to a Rust
module `packs/std/generated/<rule>.rs` (plugins.md 6.1). There is no build script:
the modules are checked in and `cargo dev gen all --check` reports a stale or
missing one as GEN001.

Each module carries `#![forbid(unsafe_code)]`, and `design/model.grmb` gives the
`std_rules` node that owns `packs/std/generated/**` no grants, so any ambient effect
in a generated module is CAP001.
