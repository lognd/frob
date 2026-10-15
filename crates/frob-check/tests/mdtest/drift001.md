<!-- mdtest: rule=DRIFT001 -->
# DRIFT001 doc binding drift

A `frob:doc` binding whose acked code or doc changed afterwards fires. The
block is built as a repository: `=== git` commits, `=== ack` records an ack,
and a later section for a path overwrites it (see `corpus.rs`).

## Code changed under an acked binding fires

```text expect=fire
=== src/lib.rs
// frob:doc docs/guide.md#greeting
pub fn greet(name: &str) -> String {
    format!("hello {name}")
}

pub fn plain(x: u32) -> u32 {
    x + 1
}
=== docs/guide.md
# Guide

## Greeting

Greets a person by name.

=== git
=== ack src/lib.rs::greet
=== src/lib.rs
// frob:doc docs/guide.md#greeting
pub fn greet(name: &str) -> String {
    format!("hi {name}")
}
```

## An acked binding with nothing changed is clean

```text expect=clean
=== src/lib.rs
// frob:doc docs/guide.md#greeting
pub fn greet(name: &str) -> String {
    format!("hello {name}")
}

pub fn plain(x: u32) -> u32 {
    x + 1
}
=== docs/guide.md
# Guide

## Greeting

Greets a person by name.

=== git
=== ack src/lib.rs::greet
```
