<!-- mdtest: rule=TOKEN006 -->
# TOKEN006 token-mode-incomplete

Mode overrides are complete. Each block is one source file in a project whose `crunk.toml` is the default preset.

## What it does

A token that overrides one mode must override every mode its file declares (`modes = { dark = "..." }`), or the missing mode silently falls back to the default value.

## Why it matters

A theme that is only half-defined renders half-themed screens.

## Remedy

Add the missing mode value, or drop the partial override.

## Examples

### A token missing a mode fires

```toml expect=fire file=design/tokens/brand.toml
[color.ink]
value = "#101820"
modes = { dark = "#f5f5f5" }

[color.body]
value = "#202830"
modes = { high = "#000000" }
```

### Every mode overridden is clean

```toml expect=clean file=design/tokens/brand.toml
[color.ink]
value = "#101820"
modes = { dark = "#f5f5f5" }
```
