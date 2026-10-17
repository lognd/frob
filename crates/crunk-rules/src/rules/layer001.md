<!-- mdtest: rule=LAYER001 -->
# LAYER001 z-index-not-a-layer

A `z-index` integer must be one of the values declared in `[layers]`. Each block is one source file in a project whose `crunk.toml` is the default preset. The preset declares 0, 100, 200 and 300.

## What it does

Flags a `z-index` whose value is a bare integer that no `[layers]` entry declares. Keywords, `var()` and `calc()` values are not judged. A project with no `[layers]` table is not checked.

## Why it matters

Stacking order that is spread over ad-hoc numbers drifts into z-index wars; named layers keep every overlay's place in one table.

## Remedy

Use the layer's token (`z-index: var(--layer-toast)`) or add the value to `[layers]`.

## Examples

### An undeclared z-index fires

```css expect=fire file=styles/base/app.css
.modal {
  z-index: 99;
}
```

### A declared value is clean

```css expect=clean file=styles/base/app.css
.modal {
  z-index: 200;
}
```

### A layer token is clean

```css expect=clean file=styles/base/app.css
.modal {
  z-index: var(--layer-overlay);
}
```
