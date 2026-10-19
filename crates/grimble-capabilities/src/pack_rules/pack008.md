<!-- mdtest: rule=PACK008 -->
# PACK008 pack-redundant-override

An override restates what the pack already says.

## What it does

Advises once per override whose value equals the pack default.

## Why it matters

Redundant overrides hide the real differences.

## Remedy

Remove the override.

## Examples

### Fires case 1

```pack expect=fire
issue redundant-override a k
```

### Clean case 2

```pack expect=clean
live a 1.0 t1
```
