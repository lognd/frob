<!-- mdtest: rule=SLOP022 -->
# SLOP022 uniform-radius

## What it does

Flags, once, three or more literal radii that share one value or that are 16px and larger in more than 60 percent of cases. Zero, percentages and `var()` radii are ignored. `[decisions] radius` silences it. Advisory.

## Why it matters

One radius on every surface reads as a default, not as a role-based decision.

## Remedy

Give roles their own radii, or declare `radius` under `[decisions]`.

## Examples

### Three identical radii fire

```css expect=fire file=styles/app.css
.c0 {
  border-radius: 16px;
}
.c1 {
  border-radius: 16px;
}
.c2 {
  border-radius: 16px;
}
```

### Varied radii are clean

```css expect=clean file=styles/app.css
.a {
  border-radius: 4px;
}
.b {
  border-radius: 8px;
}
.c {
  border-radius: 12px;
}
```

### Two radii are clean

```css expect=clean file=styles/app.css
.a {
  border-radius: 16px;
}
.b {
  border-radius: 16px;
}
```

### A declared radius decision is clean

```css expect=clean file=styles/app.css config=decide-radius
.c0 {
  border-radius: 16px;
}
.c1 {
  border-radius: 16px;
}
.c2 {
  border-radius: 16px;
}
```
