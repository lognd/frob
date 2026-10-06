<!-- mdtest: rule=MDT001 snapshot-diagnostics -->
# Snap

## fires

```rust expect=fire
let a = 1;
let b = forbidden; // error: MDT001
```

## quiet

```rust expect=clean
let ok = 1;
```
