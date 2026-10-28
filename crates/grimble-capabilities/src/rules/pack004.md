<!-- mdtest: rule=PACK004 -->
# PACK004 pack-duplicate

A pack declares the same item more than once.

## What it does

Fires once per duplicated item key.

## Why it matters

Which duplicate wins is ambiguous.

## Remedy

Remove the duplicate.

## Examples

### Fires case 1

```pack expect=fire
issue duplicate a k
```

### Clean case 2

```pack expect=clean
live a 1.0 t1
```
