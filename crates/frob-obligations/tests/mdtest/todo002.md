<!-- mdtest: rule=TODO002 -->
# TODO002 todo owned by a terminal ticket

## Fires when the ticket is done

```rust expect=fire
/* frob:todo {{DONE}} finish it */ // warn: TODO002
fn a() {}
```

## Clean when the ticket is open

```rust expect=clean
/* frob:todo {{OPEN}} finish it */
fn a() {}
```
