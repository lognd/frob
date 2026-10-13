<!-- mdtest: rule=SLOP004 -->
# SLOP004 coloured-glow-shadows

## What it does

Flags two or more `box-shadow` layers with a saturated colour and a blur of 15px or more. `[decisions] glows` silences it. Advisory.

## Why it matters

Coloured glows around cards and buttons are a dark-mode cliche that rarely serves the content.

## Remedy

Use a neutral elevation shadow, or declare `glows` under `[decisions]`.

## Examples

### Two coloured glows fire

```css expect=fire file=styles/app.css
.a {
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.5);
}
.b {
  box-shadow: 0 0 40px rgba(99, 102, 241, 0.5);
}
```

### One glow is clean

```css expect=clean file=styles/app.css
.a {
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.5);
}
```

### A neutral shadow is clean

```css expect=clean file=styles/app.css
.a {
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.2);
}
.b {
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.2);
}
```

### A declared glows decision is clean

```css expect=clean file=styles/app.css config=decide-glows
.a {
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.5);
}
.b {
  box-shadow: 0 0 40px rgba(99, 102, 241, 0.5);
}
```
