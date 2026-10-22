<!-- mdtest: rule=CRAFT010 -->
# CRAFT010 motion-policy

## What it does

Flags, once, a project whose stylesheets declare no `transition`, `animation` or `@keyframes` at all (the motion policy was deleted), and, once, a project that has motion but no `prefers-reduced-motion` media query. Advisory.

## Why it matters

Deleting motion passes every motion rule vacuously. This presence rule pairs with them so the quiet way out is reported as a missing policy.

## Remedy

Add purposeful motion with a reduced-motion twin, or turn CRAFT010 off under `[lint]` for a deliberately static design.

## Examples

### No motion at all fires

```css expect=fire file=styles/app.css
.card {
  color: #111111;
}
```

### Motion without a reduced-motion twin fires

```css expect=fire file=styles/app.css
.card {
  transition: opacity 200ms ease;
}
```

### Motion with a reduced-motion twin is clean

```css expect=clean file=styles/app.css
.card {
  transition: opacity 200ms ease;
}
@media (prefers-reduced-motion: reduce) {
  .card {
    transition: none;
  }
}
```
