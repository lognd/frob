<!-- mdtest: rule=TEST002 -->
# TEST002 heavy-profile-stale

The committed `heavy-profile.toml` no longer matches the command telemetry it is derived from.

## What it does

`frob agent heavy` records each command's wall time and disk growth; `frob agent profile` folds them into `heavy-profile.toml`, the list of commands the `pre-bash` hook sends through `frob agent heavy`. The rule fires when local telemetry exists and implies a different set of heavy commands than the profile lists. A repository without the profile, or a checkout without telemetry, is never flagged.

## Why it matters

A stale profile either lets a newly heavy command run unguarded or keeps routing a command that became cheap.

## Remedy

Run `frob agent profile` and commit the regenerated `heavy-profile.toml`.

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
