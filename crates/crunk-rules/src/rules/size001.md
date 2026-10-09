<!-- mdtest: rule=SIZE001 -->
# SIZE001 size-off-scale

Box sizes must be steps of the sizes scale. Each block is one source file in a project whose
`crunk.toml` is the default preset, which declares no `[scales] sizes`, so the spacing scale applies
(0, 4, 8, 12, 16, 24, 32, 48, 64).

## What it does

Flags a px or rem `width`, `height`, `min-width`, `min-height` or `max-height` that is not a step of
`[scales] sizes` (of `spacing` when no sizes are declared), naming the bracketing steps and the
nearest one. `max-width` is exempt by design: a maximum is a bound, not a size the design system
hands out.

## Why it matters

Fixed box sizes are the dimensions most likely to be pasted from a mock-up. Putting them on a scale
keeps components aligned to the same grid as their spacing.

## Remedy

Use the nearest `var(--size-*)` (or `var(--space-*)`) step, or add the size to `[scales] sizes`.

## Examples

### A width off the scale fires

```css expect=fire file=styles/app.css
.thumb {
  width: 45px;
}
```

### A height off the scale fires

```css expect=fire file=styles/app.css
.thumb {
  height: 100px;
}
```

### A size on the scale is clean

```css expect=clean file=styles/app.css
.thumb {
  width: 48px;
  height: 4rem;
}
```

### max-width is exempt

```css expect=clean file=styles/app.css
.prose {
  max-width: 640px;
}
```

### Percentages and viewport units are exempt

```css expect=clean file=styles/app.css
.hero {
  width: 100%;
  height: 100vh;
}
```
