<!-- mdtest: rule=COMP005 -->
# COMP005 binding-unresolved

Every component binding names an anatomy node, a declared state and a defined token.

## What it does

Fires for a binding whose node is neither the component nor listed in `[anatomy] nodes`, whose `state` the component does not declare, or whose `token` no token file or the spec defines. The finding names the node as `<component>/<node>`.

## Why it matters

A binding to nothing styles nothing, and nothing says so.

## Remedy

Fix the node, state or token name, or add the missing anatomy node, state or token.

## Examples

### An unknown node fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[states]]
id = "default"

[[bindings]]
node = "icon"
property = "color"
token = "--color-ink"
```

### An unknown token fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[bindings]]
node = "button"
property = "color"
token = "--color-nope"
```

### A resolvable binding is clean

```toml expect=clean file=design/components/button.component.toml
name = "button"

[anatomy]
nodes = ["icon"]

[[states]]
id = "default"

[[bindings]]
node = "icon"
property = "color"
state = "default"
token = "--color-ink"
```
