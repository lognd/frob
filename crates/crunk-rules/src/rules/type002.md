<!-- mdtest: rule=TYPE002 -->
# TYPE002 font-family-off-stack

Font families must come from the declared stacks. Each block is one source file in a project whose
`crunk.toml` is the default preset (families Inter, system-ui, sans-serif and no named stacks).

## What it does

Flags a `font-family` value whose members, compared case-insensitively and without quotes, are not
a prefix of any declared `[typography.stacks]` entry (of the single stack made of `families` when
none is declared). A value that uses `var()` is taken to come from the tokens and is not judged.
The rule is not fixable: choosing the replacement stack is a design decision.

## Why it matters

A font nobody declared is a font nobody licensed, loaded or tested, and it falls back differently on
every platform.

## Remedy

Use `var(--font-family-base)`, or a stack that starts like one of the declared stacks.

## Examples

### A family outside the declared stack fires

```css expect=fire file=styles/app.css
body {
  font-family: Papyrus, fantasy;
}
```

### A declared stack is clean, in any case and quoting

```css expect=clean file=styles/app.css
body {
  font-family: "inter", System-UI, sans-serif;
}
```

### A prefix of the declared stack is clean

```css expect=clean file=styles/app.css
code {
  font-family: Inter;
}
```

### A token reference is clean

```css expect=clean file=styles/app.css
body {
  font-family: var(--font-family-base);
}
```
