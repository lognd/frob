<!-- mdtest: rule=DRIFT004 -->
# DRIFT004 reattest-required

A lock entry was recorded under another file version or digest scheme and must be re-attested.

## What it does

Fires once per entry (symbol or flow) when `frob.lock` predates this build's format version or digest scheme. The digests are not comparable across schemes, so no drift rule judges such an entry.

## Why it matters

Nothing is silently accepted: an entry whose digests cannot be compared is not trusted.

## Remedy

Run `frob ack --all --reason ...` to re-record every entry under the current scheme.

## Examples

### A drifted case fires

```rust expect=fire file=src/lib.rs
pub fn bound() {}
```

### An unchanged case is clean

```rust expect=clean file=src/lib.rs
pub fn unbound() {}
```
