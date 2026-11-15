<!-- mdtest: rule=SPEC001 -->
# SPEC001 design-file-invalid

A component, screen or content file loads. Each block is one file in a project whose `crunk.toml` is the default preset.

## What it does

Reports every `design/components/*.component.toml`, `design/screens/*.screen.toml`, `design/content/*.toml` or `design/content/voice.toml` that cannot be read or does not match its schema (a syntax error, an unknown key, a missing required field). The message carries the parser's reason.

## Why it matters

A file that does not load is dropped from every other rule's input, so breaking a file makes its findings disappear and the check looks greener. This rule turns that into an error.

## Remedy

Fix the file at the reported key; the message names the key and the reason.

## Examples

### An unknown component key fires

```toml expect=fire file=design/components/readout.component.toml
name = "readout"
motion = "flicker"
```

### A valid component is clean

```toml expect=clean file=design/components/readout.component.toml
name = "readout"
```
