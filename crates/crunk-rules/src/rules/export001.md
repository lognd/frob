<!-- mdtest: rule=EXPORT001 -->
# EXPORT001 export-drift

The generated exports match the spec. Each block is one source file in a project whose `crunk.toml`
is the default preset; the case's generated `styles/tokens.css` is empty (`:root {}`), which is not
what the preset renders unless a case selects `config=tokens-current`.

## What it does

Renders every export the spec configures (CSS, Tailwind, JSON, USS, C#, DTCG) and compares it with
the file on disk. A missing or differing file is a finding that names its target. This generalises
TOKENS001, which reports the same files without the target name.

## Why it matters

A stale export means one platform builds against yesterday's design law.

## Remedy

Run `crunk tokens` to regenerate the files, and commit them.

## Examples

### An export that is not what the spec renders fires

```css expect=fire file=styles/app.css
.a {
  margin: 0;
}
```

### Exports that match the spec are clean

```css expect=clean config=tokens-current file=styles/app.css
.a {
  margin: 0;
}
```
