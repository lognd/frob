<!-- mdtest: rule=MDT001 -->
# Unresolved expected, error got

```rust expect=fire
let b = forbidden; // unresolved[hole]: MDT001
```

```rust expect=clean
let ok = 1;
```
