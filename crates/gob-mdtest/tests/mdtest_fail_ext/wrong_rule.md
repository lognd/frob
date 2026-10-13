<!-- mdtest: rule=MDT001 -->
# Wrong rule

```rust expect=fire
let b = forbidden; // error: MDT002
```

```rust expect=clean
let ok = 1;
```
