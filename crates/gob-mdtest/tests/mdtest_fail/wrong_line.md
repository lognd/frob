<!-- mdtest: rule=MDT001 -->
# Wrong line

```rust expect=fire
let a = 1;
let b = 2; // error: MDT001
let c = forbidden;
```

```rust expect=clean
let ok = 1;
```
