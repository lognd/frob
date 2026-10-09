<!-- mdtest: rule=TYPE001 -->
# TYPE001 font-size-off-scale

Font sizes must be steps of the type ramp. Each block is one source file in a project whose
`crunk.toml` is the default preset (font sizes 12, 14, 16, 20, 24, 32, 48).

## What it does

Flags a px or rem `font-size` that is not a step of `[scales] font_sizes`, naming the bracketing
steps and the nearest one. Keywords, percentages and `em` lengths carry no comparable px value and
are exempt.

## Why it matters

Every size outside the ramp weakens the hierarchy the ramp exists to enforce, and breaks the
proportions a type scale is chosen for.

## Remedy

Use the nearest `var(--font-size-*)` step, or add the size to `[scales] font_sizes` when the design
really needs a new step.

## Examples

### A size between two steps fires

```css expect=fire file=styles/app.css
h1 {
  font-size: 27px;
}
```

### A rem size off the ramp fires

```css expect=fire file=styles/app.css
p {
  font-size: 1.1rem;
}
```

### A size on the ramp is clean

```css expect=clean file=styles/app.css
h1 {
  font-size: 24px;
}
p {
  font-size: 1rem;
}
```

### Keywords and relative units are exempt

```css expect=clean file=styles/app.css
small {
  font-size: smaller;
}
em {
  font-size: 90%;
}
```
