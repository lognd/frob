<!-- mdtest: rule=TICK008 -->
# TICK008 ticket move outside a reindex

## A rename without a reindex trailer fires

```text expect=fire
rename _unfiled/renamed.md
```

## An untouched branch is clean

```text expect=clean
none
```
