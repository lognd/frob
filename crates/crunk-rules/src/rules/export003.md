<!-- mdtest: rule=EXPORT003 -->
# EXPORT003 figma-plan-limit

The Figma variables export fits the plan in `[figma]`. Each block is one source file in a project
whose `crunk.toml` is the default preset.

## What it does

Sizes every Figma collection (one per token tier): its modes, counting the default mode, and its
variables. A collection over the plan's mode limit (`[figma] plan`: 1 on starter, 10 on
professional, 20 on organization, unlimited on enterprise) or over `max_modes` / `max_variables`
is a finding naming the plan and the limit. Without a `[figma]` table nothing is checked.

## Why it matters

Figma rejects a variables import whose collection has more modes or variables than the plan allows.

## Remedy

Move to a larger plan, raise the override, or drop modes and variables from the collection.

## Examples

### A collection over the variable limit fires

```css expect=fire config=figma-tiny file=styles/app.css
.a {
  margin: 0;
}
```

### A collection within the plan is clean

```css expect=clean config=figma-professional file=styles/app.css
.a {
  margin: 0;
}
```
