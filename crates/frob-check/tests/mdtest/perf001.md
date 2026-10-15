<!-- mdtest: rule=PERF001 -->
# PERF001 check over budget

With `[perf] enforce` on, a run over `budget_ms` fires.

## A zero budget enforced fires

```text expect=fire
=== frob.toml
[perf]
enforce = true
budget_ms = 0
=== src/lib.rs
//! Library.
```

## An unenforced budget is clean

```text expect=clean
=== frob.toml
[perf]
enforce = false
budget_ms = 0
=== src/lib.rs
//! Library.
```
