<!-- mdtest: rule=DRIFT004 -->
# DRIFT004 re-attestation required

A `frob.lock` recorded under an older file version fires once per entry.

## A version 1 lock fires

```text expect=fire
=== frob.lock
version = 1

[entries."a.rs::a"]
sig = "11"
body = "22"
doc = "33"
acked_by = "Me"
acked_at = "2026-10-01T00:00:00Z"
reason = "old"
=== a.rs
pub fn a() {}
```

## A repository without a lock is clean

```text expect=clean
=== a.rs
pub fn a() {}
```
