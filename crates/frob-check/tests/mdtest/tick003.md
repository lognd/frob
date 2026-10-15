<!-- mdtest: rule=TICK003 -->
# TICK003 dangling ticket reference

Each block is `key = value` lines applied to the committed `ticket.md`.

## A parent naming a ticket that does not exist fires

```text expect=fire
parent = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
```

## An untouched card is clean

```text expect=clean
```
