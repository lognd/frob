<!-- mdtest: rule=TICK004 -->
# TICK004 home path in a committed ticket

The block is the body of a ticket committed to the ledger.

## A body naming a home directory fires

```text expect=fire
See /home/someone/projects/secret for the notes.
```

## A body with no machine path is clean

```text expect=clean
See the notes in the repository.
```
