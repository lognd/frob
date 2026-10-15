<!-- mdtest: rule=PROC001 -->
# PROC001 process spawn outside the spawner crates

Only crates listed in `[check] process_spawners` may use a spawning API.

## A spawn in an unlisted crate fires

```text expect=fire
=== frob.toml
[check]
process_spawners = ["gob-exec"]
=== crates/other/src/lib.rs
//! Other.
use std::process::Command;
```

## An exit code in an unlisted crate is clean

```text expect=clean
=== frob.toml
[check]
process_spawners = ["gob-exec"]
=== crates/other/src/lib.rs
//! Other.
use std::process::ExitCode;
```
