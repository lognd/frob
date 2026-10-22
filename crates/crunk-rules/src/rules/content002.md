<!-- mdtest: rule=CONTENT002 -->
# CONTENT002 content-over-budget

A copy key stays inside its length budget.

## What it does

Fires for each key in `design/content/*.toml` whose `text` has more characters than its `max_chars`. Characters are counted as Unicode scalar values. A key with no `max_chars` is not checked.

## Why it matters

A label that outgrows the space the design gave it wraps, truncates or breaks the layout.

## Remedy

Shorten the text, or raise `max_chars` after confirming the layout has room.

## Examples

### Text over its budget fires

```toml expect=fire file=design/content/en.toml
locale = "en"

[[key]]
id = "home.cta"
text = "Start your free trial today"
max_chars = 10
```

### Text inside its budget is clean

```toml expect=clean file=design/content/en.toml
locale = "en"

[[key]]
id = "home.cta"
text = "Start"
max_chars = 10
```
