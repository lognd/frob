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

## A reindex whose trailer names another frob version is unresolved

The replay is not run when the trailer's version is not the running one.

```text expect=unresolved
stale-reindex
```
