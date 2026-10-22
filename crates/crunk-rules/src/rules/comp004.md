<!-- mdtest: rule=COMP004 -->
# COMP004 literal-unbound

A component binding points at a design token, never at a literal value.

## What it does

Fires for each `[[bindings]]` entry that sets `value` instead of `token`, sets both, sets neither, or has a blank property. The finding names the node as `<component>/<node>`.

## Why it matters

A literal in a component spec is a value that will not follow the theme when the tokens change.

## Remedy

Replace the literal with the token that holds it, defining the token first if needed.

## Examples

### A literal fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[bindings]]
node = "button"
property = "color"
value = "#ff0000"
```

### A token is clean

```toml expect=clean file=design/components/button.component.toml
name = "button"

[[bindings]]
node = "button"
property = "color"
token = "--color-ink"
```
