<!-- mdtest: rule=TOKEN007 -->
# TOKEN007 token-scope-violation

Tokens are bound to properties they are scoped for. Each block is one source file in a project whose `crunk.toml` is the default preset.

## What it does

A token may declare `scopes = ["spacing"]`. A stylesheet declaration that reads it through `var()` in a property of another scope (`color`, `margin`, `font-size`, `border-radius`, ...) is a finding. Tokens without scopes are unrestricted.

## Why it matters

A spacing token used as a fill is almost always a slip, and scopes are how tooling restricts pickers to sensible tokens.

## Remedy

Use a token scoped for the property, or widen the token's scopes.

## Examples

### A spacing token read by color fires

```toml expect=fire config=uses-ink file=design/tokens/brand.toml
[color.ink]
value = "#101820"
scopes = ["spacing"]
```

### A color token read by color is clean

```toml expect=clean config=uses-ink file=design/tokens/brand.toml
[color.ink]
value = "#101820"
scopes = ["color"]
```
