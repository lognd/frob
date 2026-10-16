<!-- mdtest: rule=TOKEN004 -->
# TOKEN004 token-unused

Every token is used. Each block is one source file in a project whose `crunk.toml` is the default preset.

## What it does

A token is used when an examined stylesheet reads it through `var(--name)` or another token aliases it. The generated tokens sheet is not a use. The rule is skipped when no token file or no stylesheet exists.

## Why it matters

Unused tokens are dead vocabulary: they widen the design system and invite drift without serving anyone.

## Remedy

Remove the token, or use it.

## Examples

### A token no stylesheet reads fires

```toml expect=fire file=design/tokens/brand.toml
[color]
ink = "#101820"
```

### A token a stylesheet reads is clean

```toml expect=clean config=uses-ink file=design/tokens/brand.toml
[color]
ink = "#101820"
```
