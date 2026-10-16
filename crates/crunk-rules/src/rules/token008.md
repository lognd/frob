<!-- mdtest: rule=TOKEN008 -->
# TOKEN008 token-near-duplicate

Tokens do not duplicate each other. Each block is one source file in a project whose `crunk.toml` is the default preset.

## What it does

Two literal tokens with different names and the same dimension or duration, or colours within `[lint] color_tolerance`, are a finding at the second. Aliases repeat their target by design and are skipped.

## Why it matters

Near-duplicates split one decision into two names, and the next edit changes only one of them.

## Remedy

Alias one to the other, or merge them.

## Examples

### Two almost equal colours fire

```toml expect=fire file=design/tokens/brand.toml
[color]
ink = "#101820"
inkish = "#111820"
```

### Two distinct colours are clean

```toml expect=clean file=design/tokens/brand.toml
[color]
ink = "#101820"
paper = "#f5f5f0"
```
