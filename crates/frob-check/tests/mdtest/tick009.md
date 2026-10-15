<!-- mdtest: rule=TICK009 -->
# TICK009 ticket filed at the wrong path

## A ticket moved off its derived path fires

```text expect=fire
rename elsewhere/renamed.md
```

## An untouched branch is clean

```text expect=clean
none
```
