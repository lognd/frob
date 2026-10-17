<!-- mdtest: rule=DRIFT001 -->
# DRIFT001 doc-binding-drift

A `frob:doc` binding went stale: the code changed under the doc, or the doc under the code.

## What it does

Fires when a symbol bound by a `frob:doc path#slug` directive has a lock entry that no longer matches: the sig, body, doc or attr facet of the symbol changed, or the digest of the named markdown section changed. The message names the facet.

## Why it matters

A doc and the code it describes are acked together; when either moves alone, the doc may now lie.

## Remedy

Re-read the pair, then run `frob ack <symref> --reason ...` to record the new state.

## Examples

### A drifted case fires

```rust expect=fire file=src/lib.rs
pub fn bound() {}
```

### An unchanged case is clean

```rust expect=clean file=src/lib.rs
pub fn unbound() {}
```
