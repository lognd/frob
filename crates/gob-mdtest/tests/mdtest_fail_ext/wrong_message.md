<!-- mdtest: rule=MDT001 -->
# Wrong message

```rust expect=fire
let b = forbidden; // error: "no such text"
```

```rust expect=clean
let ok = 1;
```
