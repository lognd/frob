<!-- mdtest: rule=DRIFT003 -->
# DRIFT003 stale ack

An acked symbol whose signature changed with no `frob:doc` coverage fires.

## An acked signature change fires

```text expect=fire
=== src/lib.rs
pub fn plain(x: u32) -> u32 {
    x + 1
}
=== git
=== ack src/lib.rs::plain
=== src/lib.rs
pub fn plain(x: u64) -> u64 {
    x + 1
}
```

## An acked symbol left alone is clean

```text expect=clean
=== src/lib.rs
pub fn plain(x: u32) -> u32 {
    x + 1
}
=== git
=== ack src/lib.rs::plain
```
