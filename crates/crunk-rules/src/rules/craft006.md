<!-- mdtest: rule=CRAFT006 -->
# CRAFT006 scales-present

A project whose `crunk.toml` is the default preset (spacing, font sizes and radii all declared)
is clean; the fire case removes the radii.

## What it does

Flags, once per missing scale and at `crunk.toml`, a project with no type scale (`[scales]
font_sizes`), no spacing scale (`[scales] spacing`) or no radius policy (`[scales] radii` or a
`[decisions] radius` entry). Each finding names the rule it leaves with nothing to judge: TYPE001,
SPACE001, or SLOP022 and RADIUS001. Advisory.

## Why it matters

Deleting a scale passes every rule that judges against it vacuously. This presence rule pairs with
them so the quiet way out is reported as a missing scale.

## Remedy

Declare the scale under `[scales]`, or record the radius choice under `[decisions]`, or turn
CRAFT006 off under `[lint]` for a design that really has no scale.

## Examples

### No radius policy fires

```css expect=fire file=styles/app.css config=no-radii
.card {
  color: #111111;
}
```

### A declared radius decision is clean

```css expect=clean file=styles/app.css config=no-radii-decided
.card {
  color: #111111;
}
```

### The default preset's scales are clean

```css expect=clean file=styles/app.css
.card {
  color: #111111;
}
```
