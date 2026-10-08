<!-- mdtest: rule=COLOR001 -->
# COLOR001 color-off-palette

A colour literal in a stylesheet, a custom property or a JSX style prop must be a palette colour.
Each block below is one source file in a project whose `crunk.toml` is the default preset (palette
`ink` #1a1a1a, `paper` #fafaf7, `accent` #2f6fed); the generated tokens sheet is indexed and empty.

## What it does

Flags a colour literal (hex, `rgb()`, `hsl()` or a named colour) that is not a palette colour, and
names the nearest palette token with its distance. A translucent variant of an opaque palette colour
is not a new colour and is clean; a translucent palette entry needs the exact rgba match. The
generated tokens sheet is skipped because the palette literals live there. The rule runs once per
declared mode. A project with no stylesheet to judge is Unresolved, never clean.

## Why it matters

A colour typed by hand drifts from the palette the moment the palette changes, and no review sees
it. Routing every colour through a token keeps one place to change and one place to audit.

## Remedy

Use `var(--color-...)` for the nearest palette entry, or add the colour to `[palette]` in
`crunk.toml` when it is a new brand colour. Beyond `[lint] color_tolerance` the nearest entry is a
different colour and the replacement is a design decision.

## Examples

### A hex literal outside the palette fires

```css expect=fire file=styles/app.css
.btn {
  color: #ff0000;
}
```

### A custom property holding an off-palette literal fires

```css expect=fire file=styles/app.css
:root {
  --brand: #123456;
}
```

### A named colour in a JSX style prop fires

```tsx expect=fire file=src/Button.tsx
export function Button() {
  return <button style={{ color: "red" }} />;
}
```

### A palette colour is clean

```css expect=clean file=styles/app.css
.btn {
  color: #1a1a1a;
  background: #2f6fed;
}
```

### A translucent variant of an opaque palette colour is clean

```css expect=clean file=styles/app.css
.shade {
  background: rgba(26, 26, 26, 0.5);
}
```

### A token reference and a non-colour keyword are clean

```css expect=clean file=styles/app.css
.btn {
  color: var(--color-ink);
  border-color: inherit;
  padding: 4px 8px;
}
```

### The generated tokens sheet is skipped

```css expect=clean file=styles/tokens.css
:root {
  --color-brand: #123456;
}
```
