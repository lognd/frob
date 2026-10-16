<!-- mdtest: rule=TOKEN002 -->
# TOKEN002 token-file-invalid

An authored token file compiles. Each block is one source file in a project whose `crunk.toml` is the default preset.

## What it does

Compiles every `design/tokens/*.toml` file with the token dialect. A file that is not valid TOML, a token whose path or value is malformed (an unknown `$type`, a bad colour, a bad `tier`), or two tokens that produce one custom property name is a finding. A broken alias is TOKEN003.

## Why it matters

A file that does not compile contributes nothing: every token in it is silently missing from the exports and the lint.

## Remedy

Fix the file at the reported token; the message names the key and the reason.

## Examples

### A malformed colour fires

```toml expect=fire file=design/tokens/brand.toml
[color]
ink = "#12"
```

### A valid file is clean

```toml expect=clean file=design/tokens/brand.toml
[color]
ink = "#101820"
```
