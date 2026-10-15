<!-- mdtest: rule=TICK001 -->
# TICK001 ticket card disagrees with its events

Each block is `key = value` lines applied to the committed `ticket.md` of a
ledger holding one ticket.

## A hand-edited title fires

```text expect=fire
title = "Edited by hand"
```

## An untouched card is clean

```text expect=clean
```
