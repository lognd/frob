<!-- mdtest: rule=LAYER001 -->
# LAYER001 z-index-off-layers

A `z-index` must be one of the declared layers. Each block is one source file in a project whose
`crunk.toml` is the default preset (layers 0, 100, 200, 300).

## What it does

Flags a `z-index: <integer>` whose value is not among the values of `[layers]`, naming the declared
values. `auto` and values that are not plain integers (`var()`, `calc()`) are exempt. A project that
declares no layers has no law to judge against; the rule is then inapplicable and the skip is
reported.

## Why it matters

A stray `z-index: 9999` wins the stacking contest today and loses it to the next one tomorrow.
Named layers keep the stacking order a decision made once.

## Remedy

Use the `var(--layer-*)` token of the layer the element belongs to, or add the value to `[layers]`.

## Examples

### A z-index outside the layers fires

```css expect=fire file=styles/app.css
.modal {
  z-index: 99;
}
```

### A negative z-index outside the layers fires

```css expect=fire file=styles/app.css
.under {
  z-index: -1;
}
```

### A declared layer value is clean

```css expect=clean file=styles/app.css
.menu {
  z-index: 100;
}
```

### auto and non-integer values are exempt

```css expect=clean file=styles/app.css
.a {
  z-index: auto;
}
.b {
  z-index: var(--layer-toast);
}
```
