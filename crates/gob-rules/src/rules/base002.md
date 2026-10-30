<!-- mdtest: rule=BASE002 -->
# BASE002 baseline-ticket-dead

A baseline table whose burn-down ticket is closed or dropped without a successor.

## What it does

Looks up the `ticket` of every table in `frob-baseline.toml` and fires when it is closed, or dropped with no live successor. A ticket the ledger cannot find is reported Unresolved, never clean.

## Why it matters

Debt must not outlive its plan: a table whose ticket is gone has nobody burning it down.

## Remedy

Point the table at a live burn-down ticket (a change BASE001 allows only through a fresh `adopt`), or fix the findings so `frob baseline prune` deletes the table.

## Examples

### A table with a dead ticket fires

```toml expect=fire file=frob-baseline.toml config=ticket-dead
version = 1

[rules.PM009]
reason = "adopting the rule"
ticket = "~61BXXNJ"
findings = [
  "0000000000000000000000000000000000000000000000000000000000000001",
]
```

### A table with a live ticket is clean

```toml expect=clean file=frob-baseline.toml config=ticket-live
version = 1

[rules.PM009]
reason = "adopting the rule"
ticket = "~61BXXNJ"
findings = [
  "0000000000000000000000000000000000000000000000000000000000000001",
]
```
