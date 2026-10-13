<!-- mdtest: rule=MDT001 -->
# Differing reason

```rust expect=fire
let b = unsure; // unresolved[partial]: MDT001
```

```rust expect=clean
let ok = 1;
```
