<!-- mdtest: rule=RADIUS001 -->
# RADIUS001 radius-off-scale

Corner radii must be steps of the radius scale. Each block is one source file in a project whose
`crunk.toml` is the default preset (radii 0, 4, 8, 16).

## What it does

Flags a px or rem `border-radius` (or a corner longhand) that is not a step of `[scales] radii`,
naming the bracketing steps and the nearest one. A project that declares no radii has no scale to
judge against; the rule is then inapplicable and the skip is reported.

## Why it matters

Corner radii are the most visible detail of a component family: one 6px card among 4px and 8px
neighbours reads as a mistake, not as a choice.

## Remedy

Use the nearest `var(--radius-*)` step, or add the radius to `[scales] radii`.

## Examples

### A radius between two steps fires

```css expect=fire file=styles/app.css
.card {
  border-radius: 6px;
}
```

### A corner longhand fires

```css expect=fire file=styles/app.css
.card {
  border-top-left-radius: 10px;
}
```

### A radius on the scale is clean

```css expect=clean file=styles/app.css
.card {
  border-radius: 8px;
  border-top-left-radius: 0;
}
```

### A percentage radius is exempt

```css expect=clean file=styles/app.css
.avatar {
  border-radius: 50%;
}
```
