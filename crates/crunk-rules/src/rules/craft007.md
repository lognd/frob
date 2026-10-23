<!-- mdtest: rule=CRAFT007 -->
# CRAFT007 elevation-system

Shadows share one light.

## What it does

Compares every `box-shadow` layer (and `--shadow*` or `*elevation*` property) with the first one: an offset pointing more than 15 degrees away, or a blur-to-distance ratio more than 3 times apart, fires at that declaration. Inset, `var()` and zero-offset layers are skipped, and fewer than two layers is quiet. Advisory.

## Why it matters

Shadows cast in different directions read as different light sources, which flattens depth.

## Remedy

Point every shadow the same way and grow the blur with the distance, or turn CRAFT007 off under `[lint]`.

## Examples

### A shadow cast the other way fires

```css expect=fire file=styles/app.css
.a {
  box-shadow: 0 4px 8px #00000033;
}
.b {
  box-shadow: 0 -4px 8px #00000033;
}
```

### Shadows lit alike are clean

```css expect=clean file=styles/app.css
.a {
  box-shadow: 0 2px 4px #00000033;
}
.b {
  box-shadow: 0 8px 16px #00000033;
}
```
