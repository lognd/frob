<!-- mdtest: rule=COLOR001 -->
# COLOR001 colour literal outside the palette

Each block is one source file in a repository whose `crunk.toml` is the default preset
(palette `ink` #1a1a1a, `paper` #fafaf7, `accent` #2f6fed). The declarations are read by the
shared `style` capability, from CSS and from TSX inline style objects alike.

## A hex literal outside the palette fires

```css expect=fire file=styles/app.css
.btn {
  color: #ff0000;
}
```

## A named colour outside the palette fires in a TSX style prop

```tsx expect=fire file=src/Button.tsx
export function Button() {
  return <button style={{ color: "red" }} />;
}
```

## A custom property holding an off-palette literal fires

```css expect=fire file=styles/app.css
:root {
  --brand: #123456;
}
```

## A palette colour is clean

```css expect=clean file=styles/app.css
.btn {
  color: #1a1a1a;
  background: #2f6fed;
}
```

## A translucent variant of an opaque palette colour is clean

```css expect=clean file=styles/app.css
.shade {
  background: rgba(26, 26, 26, 0.5);
}
```

## A reference to a token and a non-colour keyword are clean

```css expect=clean file=styles/app.css
.btn {
  color: var(--color-ink);
  border-color: inherit;
  padding: 4px 8px;
}
```

## The generated tokens sheet is skipped

```css expect=clean file=styles/tokens.css
:root {
  --color-brand: #123456;
}
```
