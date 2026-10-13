<!-- mdtest: rule=SLOP014 -->
# SLOP014 eyebrow-chrome

## What it does

Flags three or more short (four words or fewer) labels in an element marked `uppercase`, `eyebrow`, `kicker` or `overline` that sit directly above an `h1` or `h2`. `[decisions] eyebrows` silences it. Advisory.

## Why it matters

A small caps kicker above every heading is decoration that repeats instead of informing.

## Remedy

Drop the labels that restate the heading, or declare `eyebrows` under `[decisions]`.

## Examples

### Three eyebrows fire

```tsx expect=fire file=src/Page.tsx
export function Page() {
  return (
    <main>
      <p className="uppercase tracking-widest">Label one</p>
      <h2>Heading one</h2>
      <p className="uppercase tracking-widest">Label two</p>
      <h2>Heading two</h2>
      <p className="uppercase tracking-widest">Label three</p>
      <h2>Heading three</h2>
    </main>
  );
}
```

### A single eyebrow is clean

```tsx expect=clean file=src/Page.tsx
export function Page() {
  return (
    <main>
      <p className="uppercase">Label one</p>
      <h2>Heading one</h2>
    </main>
  );
}
```

### Plain headings are clean

```tsx expect=clean file=src/Page.tsx
export function Page() {
  return (
    <main>
      <h2>Heading one</h2>
      <h2>Heading two</h2>
      <h2>Heading three</h2>
    </main>
  );
}
```

### A declared eyebrows decision is clean

```tsx expect=clean file=src/Page.tsx config=decide-eyebrows
export function Page() {
  return (
    <main>
      <p className="uppercase tracking-widest">Label one</p>
      <h2>Heading one</h2>
      <p className="uppercase tracking-widest">Label two</p>
      <h2>Heading two</h2>
      <p className="uppercase tracking-widest">Label three</p>
      <h2>Heading three</h2>
    </main>
  );
}
```
