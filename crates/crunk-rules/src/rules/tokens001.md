<!-- mdtest: rule=TOKENS001 -->
# TOKENS001 tokens-file-drift

The generated token files match the spec. Each block is one source file in a project whose
`crunk.toml` is the default preset; the case's generated `styles/tokens.css` is empty (`:root {}`),
which is not what the preset renders unless a case selects `config=tokens-current`.

## What it does

Renders the token files the spec configures (the CSS file, `[tailwind] tokens_file`,
`[tokens] json_file`) and compares them with the files on disk: a missing file or one that differs
is a finding that names the file. The CSS file is compared byte for byte after line-ending
normalization, the JSON files after parsing, so a formatter re-wrapping them is not drift. A
difference in only the generated banner line is reported as such. A spec whose tokens collide on a
name cannot be rendered; the rule is then Unresolved.

## Why it matters

A stale tokens file means the stylesheet and the design law disagree: every `var(--space-*)`
resolves against yesterday's scale.

## Remedy

Run `crunk tokens` to regenerate the files, and commit them.

## Examples

### A tokens file that is not what the spec renders fires

```css expect=fire file=styles/app.css
.a {
  margin: 0;
}
```

### Token files that match the spec are clean

```css expect=clean config=tokens-current file=styles/app.css
.a {
  margin: 0;
}
```
