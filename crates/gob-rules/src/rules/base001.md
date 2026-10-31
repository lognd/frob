<!-- mdtest: rule=BASE001 -->
# BASE001 baseline-grew

A baseline table gained a key or changed its ticket against the base tip.

## What it does

Compares `frob-baseline.toml` at the checked tree with the base tip and fires for every rule table that lists a fingerprint the base did not, or whose `ticket` changed. A table that is new at head is the `frob baseline adopt` creation event and is not growth. Removing keys is always allowed.

## Why it matters

The baseline is a pool that only shrinks. A hand-added key silences a new finding without fixing it, which is the debt growth the baseline exists to prevent.

## Remedy

Remove the added keys and fix the finding, or run `frob baseline adopt <RULE> --reason R --ticket T` for a rule that has no table yet.

## Examples

### A table that gained a key fires

```toml expect=fire file=frob-baseline.toml config=base-has-one-key
version = 1

[rules.PM009]
reason = "adopting the rule"
ticket = "~61BXXNJ"
findings = [
  "0000000000000000000000000000000000000000000000000000000000000001",
  "0000000000000000000000000000000000000000000000000000000000000002",
]
```

### A table that only shrank is clean

```toml expect=clean file=frob-baseline.toml config=base-has-one-key
version = 1

[rules.PM009]
reason = "adopting the rule"
ticket = "~61BXXNJ"
findings = [
  "0000000000000000000000000000000000000000000000000000000000000001",
]
```
