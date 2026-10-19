<!-- mdtest: rule=PACK005 -->
# PACK005 pack-malformed

A pack file is malformed.

## What it does

Fires once per pack with a file that does not parse.

## Why it matters

A malformed pack cannot be trusted to say what it means.

## Remedy

Repair the pack file.

## Examples

### Fires case 1

```pack expect=fire
issue malformed a bad toml
```

### Clean case 2

```pack expect=clean
live a 1.0 t1
```
