<!-- mdtest: rule=PACK003 -->
# PACK003 pack-detector-unavailable

A pack detector is unavailable, so its detections are skipped.

## What it does

Warns once per detector a pack declares that this build cannot run.

## Why it matters

Skipped detections look like a clean result.

## Remedy

Install or enable the detector, or drop it from the pack.

## Examples

### Fires case 1

```pack expect=fire
issue detector-unavailable a tree-sitter-x
```

### Clean case 2

```pack expect=clean
live a 1.0 t1
```
