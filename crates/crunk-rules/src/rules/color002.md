<!-- mdtest: rule=COLOR002 -->
# COLOR002 undefined-token-reference

A `var(--color-x)` that looks like a design token must name a custom property that exists. Each
block is one source file in a project whose `crunk.toml` is the default preset; the generated tokens
sheet is indexed and empty, and the spec exports `--color-ink`, `--color-paper` and `--color-accent`.

## What it does

Flags a `var()` reference whose name starts with a configured token prefix and is defined neither by
the spec's token export nor by a custom property of any indexed sheet. When a place a definition
could live was not indexed (the generated tokens sheet, a css file outside `css_root`, a file that
failed to parse) the rule cannot tell a typo from a definition it never saw, and reports Unresolved
instead of a clean pass. A project with no stylesheet to judge is Unresolved too.

## Why it matters

An undefined custom property makes the declaration invalid at computed-value time: the browser
silently falls back to the inherited or initial value, so the colour, space or size just disappears.

## Remedy

Fix the name (the nearest token is usually one character away), define the custom property, or
export the token from `crunk.toml`. For an Unresolved result, index the missing source.

## Examples

### A token-shaped reference nothing defines fires

```css expect=fire file=styles/app.css
.btn {
  color: var(--color-missing);
}
```

### A reference to an exported token is clean

```css expect=clean file=styles/app.css
.btn {
  color: var(--color-ink);
}
```

### A reference to a property a sheet defines is clean

```css expect=clean file=styles/app.css
:root {
  --color-local: #1a1a1a;
}
.btn {
  color: var(--color-local);
}
```

### A reference outside the token namespaces is not judged

```css expect=clean file=styles/app.css
.btn {
  color: var(--vendor-widget-color);
}
```

### An unindexed generated sheet leaves the answer Unresolved

```css expect=fire file=styles/app.css config=no-tokens
.btn {
  color: var(--color-missing);
}
```
