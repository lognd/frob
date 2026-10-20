<!-- mdtest: rule=TODO002 -->
# TODO002 todo owned by a terminal ticket

A repository with a ledger of one open and one done ticket; `{{OPEN}}` and `{{DONE}}` expand to their ids.

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

## Unresolved when the ledger holds no ticket to own the todo

The ledger exists but is empty (`{{VACUOUS}}`), so TODO002 examined zero subjects and says so
instead of passing.

```rust expect=unresolved reason=vacuous
/* frob:todo T-9999 finish it */ // {{VACUOUS}}
fn a() {}
```
