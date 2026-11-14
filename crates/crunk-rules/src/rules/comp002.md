<!-- mdtest: rule=COMP002 -->
# COMP002 variants-incomplete

A component variant matrix lists every combination of its axis props exactly once.

## What it does

Fires when a `[[variants]]` cell names an unknown axis or value, omits an axis, repeats another cell, when variants exist but no enum prop sets `axis = true`, or when the cells cover fewer combinations than the axes allow. Every combination of the axes' values is enumerated and resolved to a cell; each combination no cell renders is named in the finding (up to eight, then a count). Components are specs, not scenes, so "render" here means resolving the combination to a declared cell.

## Why it matters

A hole in the matrix is a variant nobody designed and nobody will notice shipping.

## Remedy

Add the missing cells, drop the repeats, and mark the enum props that vary as `axis = true`.

## Examples

### One of two sizes covered fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[props]]
name = "size"
kind = "enum"
values = ["sm", "lg"]
axis = true

[[variants]]
axes = { size = "sm" }
```

### Every size covered is clean

```toml expect=clean file=design/components/button.component.toml
name = "button"

[[props]]
name = "size"
kind = "enum"
values = ["sm", "lg"]
axis = true

[[variants]]
axes = { size = "sm" }

[[variants]]
axes = { size = "lg" }
```
