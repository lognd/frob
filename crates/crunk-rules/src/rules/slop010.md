<!-- mdtest: rule=SLOP010 -->
# SLOP010 font-unchosen

## What it does

Flags a literal `font-family` led by Inter, Roboto, Arial, system-ui or a second-wave default (Space Grotesk, Geist, Instrument Serif, Fraunces, Syne). `[decisions] fonts` records the rationale and silences it. Advisory: a chosen Inter is fine.

## Why it matters

The default font is the font nobody chose; it makes unrelated products look alike.

## Remedy

Pick a face for a stated reason and declare `fonts` under `[decisions]`.

## Examples

### Inter first fires

```css expect=fire file=styles/app.css
body {
  font-family: Inter, sans-serif;
}
```

### Space Grotesk first fires

```css expect=fire file=styles/app.css
h1 {
  font-family: "Space Grotesk", sans-serif;
}
```

### A distinct face is clean

```css expect=clean file=styles/app.css
body {
  font-family: Gotham, sans-serif;
}
```

### A declared fonts decision is clean

```css expect=clean file=styles/app.css config=decide-fonts
body {
  font-family: Inter, sans-serif;
}
```
