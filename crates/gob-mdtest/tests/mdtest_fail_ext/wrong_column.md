<!-- mdtest: rule=MDT001 -->
# Wrong column

```rust expect=fire
let b = forbidden; // error: [1]
```

```rust expect=clean
let ok = 1;
```
