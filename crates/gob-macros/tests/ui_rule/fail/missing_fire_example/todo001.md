<!-- mdtest: rule=TODO001 -->
# TODO001 bare-work-marker

A work marker comment must name a ticket through a `frob:todo` directive.

## What it does

Flags a comment containing a bare work marker that no `frob:todo` directive owns.

## Why it matters

An unowned marker is work nobody tracks.

## Remedy

File a ticket, then write `frob:todo <ulid>` on the comment.

## Examples

### A bare marker fires

```rust expect=nothing file=src/lib.rs
// TODO fix this
fn f() {}
```

### An owned marker is clean

```rust expect=clean file=src/lib.rs
// TODO fix this frob:todo 01ABC
fn f() {}
```
