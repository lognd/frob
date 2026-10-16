<!-- mdtest: rule=EXPORT002 -->
# EXPORT002 export-parity

The same token resolves to the same value in every export. Each block is one source file in a
project whose `crunk.toml` is the default preset.

## What it does

Reads the CSS and JSON exports from disk and renders the USS and C# exports, then compares every
token across the targets after reducing values to a number or a colour (so `16px` and `16f` agree).
A token that two targets resolve differently is a finding naming both values and targets.

## Why it matters

One design system shipped to web and Unity must not drift apart because one file was edited by hand.

## Remedy

Run `crunk tokens` to regenerate every export from the spec.

## Examples

### A hand-edited CSS value fires

```css expect=fire config=tokens-divergent file=styles/app.css
.a {
  margin: 0;
}
```

### Freshly generated exports are clean

```css expect=clean config=tokens-current file=styles/app.css
.a {
  margin: 0;
}
```
