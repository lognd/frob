<!-- mdtest: rule=SLOP040 -->
# SLOP040 emoji-as-icon

## What it does

Flags a pictograph as the first character of an `li`, heading, `button` or `a` label in a JSX source, or at the start of a CSS `content` or `list-style` string. Numeric character references and CSS escapes are read as the character they name. `[decisions] emoji` silences it. Warn.

## Why it matters

Emoji used as bullets and icons render differently on every platform and read as filler.

## Remedy

Use an icon component or plain text, or declare `emoji` under `[decisions]`.

## Examples

### An emoji list item fires

```tsx expect=fire file=src/Page.tsx
export function Page() {
  return (
    <main>
      <ul>
        <li>&#x1F680; Fast</li>
      </ul>
    </main>
  );
}
```

### An emoji CSS marker fires

```css expect=fire file=styles/app.css
li::before {
  content: "\1F680";
}
```

### A plain list item is clean

```tsx expect=clean file=src/Page.tsx
export function Page() {
  return (
    <main>
      <ul>
        <li>Fast</li>
      </ul>
    </main>
  );
}
```

### A declared emoji decision is clean

```tsx expect=clean file=src/Page.tsx config=decide-emoji
export function Page() {
  return (
    <main>
      <ul>
        <li>&#x1F680; Fast</li>
      </ul>
    </main>
  );
}
```
