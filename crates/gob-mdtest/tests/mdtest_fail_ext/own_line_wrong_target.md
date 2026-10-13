<!-- mdtest: rule=MDT001 -->
# Own-line marker targets the next line

```rust expect=fire
// error: MDT001

let b = forbidden;
```

```rust expect=clean
let ok = 1;
```
