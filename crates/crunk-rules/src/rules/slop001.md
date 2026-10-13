<!-- mdtest: rule=SLOP001 -->
# SLOP001 default-palette-accent

## What it does

Flags a palette entry or a colour literal within two deltaE_OK points of a Tailwind indigo, violet or purple 400-700 stop. `[decisions] accent` records that the purple is the brand and silences the rule. Advisory: real purple brands exist.

## Why it matters

An indigo accent nobody picked is the strongest single tell of a generated interface.

## Remedy

Choose an accent on purpose, or declare `accent` under `[decisions]` with the reason.

## Examples

### A literal Tailwind indigo fires

```css expect=fire file=styles/app.css
.cta {
  background: #6366f1;
}
```

### A default-indigo palette accent fires

```css expect=fire file=styles/app.css config=palette-indigo
.cta {
  margin: 0;
}
```

### A chosen accent is clean

```css expect=clean file=styles/app.css
.cta {
  background: #2f6fed;
}
```

### A declared accent decision is clean

```css expect=clean file=styles/app.css config=decide-accent
.cta {
  background: #6366f1;
}
```
