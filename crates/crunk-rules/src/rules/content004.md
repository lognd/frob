<!-- mdtest: rule=CONTENT004 -->
# CONTENT004 content-key-duplicate

Every content key is defined in exactly one file.

## What it does

Fires once for each key that more than one file in `design/content/*.toml` defines, naming the key and every file that defines it.

## Why it matters

Two definitions of one key leave the rendered copy depending on load order, so an edit to one file can silently change nothing.

## Remedy

Keep the key in one file and delete the other definitions, or rename one of them.

## Examples

### A key defined in two files fires

```toml expect=fire file=design/content/en.toml config=content-dup
locale = "en"

[[key]]
id = "home.hero"
text = "Welcome back"
```

### A key defined once is clean

```toml expect=clean file=design/content/en.toml
locale = "en"

[[key]]
id = "home.hero"
text = "Welcome back"
```
