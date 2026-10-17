<!-- mdtest: rule=PROC001 -->
# PROC001 process-outside-exec

A crate outside the repository's declared spawners uses a process-spawning API.

## What it does

A repository-local policy: only repositories that list crates in `[check] process_spawners` are checked, so consumers never see it. Matches `Command`, `Child`, `Stdio` and exec/spawn APIs, never `ExitCode`, `exit` or `id`.

## Why it matters

Spawning processes outside the listed crates bypasses the runner's timeout, logging and sandbox handling.

## Remedy

Move the call into a listed crate or route it through `gob_exec::Runner`.

## Examples

### Fires case 1

```rust expect=fire file=crates/app/src/main.rs
use std::process::Command;
fn main() { let _ = Command::new("ls"); }
```

### Clean case 1

```rust expect=clean file=crates/app/src/main.rs
fn main() { println!("hi"); }
```
