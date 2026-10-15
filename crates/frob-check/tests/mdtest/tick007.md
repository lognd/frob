<!-- mdtest: rule=TICK007 -->
# TICK007 reindex commit that does not replay

The ledger lives on an orphan branch; the first line of the block is the
scenario.

## A reindex-trailer commit carrying a hand edit fires

```text expect=fire
edit smuggled line
```

## A genuine reindex is clean

```text expect=clean
reindex
```
