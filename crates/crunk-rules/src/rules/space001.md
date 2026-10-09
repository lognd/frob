<!-- mdtest: rule=SPACE001 -->
# SPACE001 spacing-off-scale

Margins, paddings, gaps and insets must be steps of the spacing scale. Each block below is one source
file in a project whose `crunk.toml` is the default preset (spacing 0, 4, 8, 12, 16, 24, 32, 48, 64;
`fix_tolerance` 0.15).

## What it does

Flags a px or rem length in `margin`, `padding`, `gap`, `inset` or an edge offset (and their
longhands) that is not a step of `[scales] spacing`, and names the two steps it falls between and the
nearest one. A negative length is judged by its magnitude. Zero, percentages, `auto`, `calc()` and
other units carry no comparable px value and are exempt. A project with no stylesheet to judge is
Unresolved, never clean.

## Why it matters

A spacing value off the scale is a one-off that no token will ever update: the layout drifts one
pixel at a time until nothing lines up.

## Remedy

Use the nearest `var(--space-*)` step. Within `[lint] fix_tolerance` the snap is a safe mechanical
fix; beyond it, the value is a different design decision and needs a person.

## Examples

### A margin between two steps fires

```css expect=fire file=styles/app.css
.card {
  margin: 13px;
}
```

### One bad length in a shorthand fires

```css expect=fire file=styles/app.css
.card {
  padding: 8px 13px;
}
```

### A rem length is converted before it is compared

```css expect=fire file=styles/app.css
.card {
  gap: 0.8rem;
}
```

### A style prop in TSX fires

```tsx expect=fire file=src/Card.tsx
export const Card = () => <div style={{ padding: 13 }} />;
```

### Lengths on the scale are clean

```css expect=clean file=styles/app.css
.card {
  margin: 12px;
  padding: 8px 16px;
  gap: 1rem;
  top: 0;
}
```

### Percentages, auto, calc and other units are exempt

```css expect=clean file=styles/app.css
.card {
  margin: 0 auto;
  padding: 5%;
  gap: calc(100% - 13px);
  inset: 3vh;
}
```

### Properties outside the spacing family are not judged

```css expect=clean file=styles/app.css
.card {
  line-height: 13px;
  border-width: 3px;
}
```
