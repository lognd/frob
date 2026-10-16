<!-- mdtest: rule=TOKEN009 -->
# TOKEN009 token-deprecated-used

Deprecated tokens are not used. Each block is one source file in a project whose `crunk.toml` is the default preset.

## What it does

A token with `deprecated = "reason"` may not be aliased by another token or read through `var()` by an examined stylesheet. The deprecated token's own definition is not a use.

## Why it matters

Deprecation is a promise to remove; every remaining use blocks the removal.

## Remedy

Move the use to the replacement the reason names.

## Examples

### A stylesheet reading a deprecated token fires

```toml expect=fire config=uses-ink file=design/tokens/brand.toml
[color.ink]
value = "#101820"
deprecated = "use color.text"
```

### A token not deprecated is clean

```toml expect=clean config=uses-ink file=design/tokens/brand.toml
[color.ink]
value = "#101820"
```
