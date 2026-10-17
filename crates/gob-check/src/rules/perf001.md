<!-- mdtest: rule=PERF001 -->
# PERF001 check-over-budget

The built-in stages of a check run took longer than the `[perf]` budget.

## What it does

The built-in stages of a check run took longer than the `[perf]` budget.

## Why it matters

A check that grows past its budget stops being run; the budget keeps the gate fast enough to use.

## Remedy

Only raised when the enforcement knob of the perf table is on. The breakdown from `frob check --timing` shows which stage grew; a cold cache (first run, new checkout) legitimately exceeds the warm budget, so rerun before treating it as a regression.

## Examples

### Fires case 1

```toml expect=fire file=frob.toml
[perf]
enforce = true
budget_ms = 1
```

### Clean case 1

```toml expect=clean file=frob.toml
[perf]
enforce = true
budget_ms = 60000
```
