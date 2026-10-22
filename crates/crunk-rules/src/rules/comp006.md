<!-- mdtest: rule=COMP006 -->
# COMP006 a11y-contract-incomplete

An interactive component carries an a11y contract: a role, an accessible-name source, a keyboard map and a target at least 24 pixels wide.

## What it does

Fires for a component whose `kinds` lists `interactive` and whose `[a11y]` table lacks a role, a name source or keyboard keys, or whose `min_target` is absent or below 24.

## Why it matters

Interactive components that are not reachable and nameable are not usable by everyone.

## Remedy

Complete the `[a11y]` table, or drop the kind if the component is not interactive.

## Examples

### No contract fires

```toml expect=fire file=design/components/button.component.toml
name = "button"
kinds = ["interactive"]
```

### A target of 23 fires

```toml expect=fire file=design/components/button.component.toml
name = "button"
kinds = ["interactive"]

[a11y]
role = "button"
name_source = "label"
keyboard = { Enter = "activate" }
min_target = 23
```

### A complete contract is clean

```toml expect=clean file=design/components/button.component.toml
name = "button"
kinds = ["interactive"]

[a11y]
role = "button"
name_source = "label"
keyboard = { Enter = "activate" }
min_target = 44
```
