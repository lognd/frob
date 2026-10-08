<!-- mdtest: rule=TYPE003 -->
# TYPE003 font-weight-off-scale

Font weights must be declared weights. Each block is one source file in a project whose `crunk.toml`
is the default preset (weights 400, 500, 700).

## What it does

Flags a numeric `font-weight` that is not in `[typography] weights`. `normal` and `bold` count as
400 and 700; `bolder`, `lighter` and the CSS-wide keywords are relative and exempt.

## Why it matters

A weight that was never loaded is rendered by synthesis or by the nearest face the browser picks,
and differs between platforms.

## Remedy

Use a declared weight, or declare the weight in `[typography]` and load the face.

## Examples

### A weight nobody declared fires

```css expect=fire file=styles/app.css
h1 {
  font-weight: 600;
}
```

### A declared weight and the normal and bold keywords are clean

```css expect=clean file=styles/app.css
h1 {
  font-weight: 700;
}
p {
  font-weight: normal;
}
strong {
  font-weight: bold;
}
```

### Relative keywords are exempt

```css expect=clean file=styles/app.css
b {
  font-weight: bolder;
}
```
