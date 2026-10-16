<!-- mdtest: rule=TOKEN003 -->
# TOKEN003 token-alias-broken

Token aliases resolve. Each block is one source file in a project whose `crunk.toml` is the default preset.

## What it does

An alias (`"{color.ink}"`) must name a token in the same file and its chain must not loop. Aliases in modes are checked too. Each token file is self-contained, so an alias never reaches another file.

## Why it matters

A dangling or cyclic alias has no value; every export of it would be wrong or absent.

## Remedy

Point the alias at a token that exists in the file, or break the cycle.

## Examples

### An alias to a missing token fires

```toml expect=fire file=design/tokens/brand.toml
[color]
ink = "#101820"
body = "{color.missing}"
```

### A cycle fires

```toml expect=fire file=design/tokens/brand.toml
[color]
a = "{color.b}"
b = "{color.a}"
```

### A resolving alias is clean

```toml expect=clean file=design/tokens/brand.toml
[color]
ink = "#101820"
body = "{color.ink}"
```
