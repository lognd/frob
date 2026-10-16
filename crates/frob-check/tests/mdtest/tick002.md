<!-- mdtest: rule=TICK002 -->
# TICK002 frob:ticket directive naming an unknown ticket

The block is a new file in a scoped run; `{ticket}` expands to the id of the
ticket under test, which exists on the base ref.

## A directive naming a ticket absent from the base fires

```rust expect=fire file=src/a/lib.rs
// frob:ticket 01ARZ3NDEKTSV4RRFFQ69G5FAV
```

## A directive naming the ticket under test is clean

```rust expect=clean file=src/a/lib.rs
// frob:ticket {ticket}
```
