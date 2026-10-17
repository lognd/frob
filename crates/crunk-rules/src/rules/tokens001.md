<!-- mdtest: rule=TOKENS001 -->
# TOKENS001 generated-tokens-stale

The generated tokens sheet must equal what `crunk tokens` writes for the current `crunk.toml`. `config=stale-tokens` gives the mdtest project an expected sheet that differs from the one on disk.

## What it does

Compares each generated file to the exporter's output for the current spec and flags a file that is missing or differs.

## Why it matters

A stale tokens sheet means the CSS the project ships disagrees with the design spec.

## Remedy

Run `crunk tokens` and commit the result.

## Examples

### A sheet that differs from the exporter output fires

```css expect=fire file=styles/base/app.css config=stale-tokens
.card {
  display: block;
}
```

### No expected output means nothing is judged

```css expect=clean file=styles/base/app.css
.card {
  display: block;
}
```
