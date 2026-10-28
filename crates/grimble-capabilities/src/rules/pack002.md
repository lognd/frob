<!-- mdtest: rule=PACK002 -->
# PACK002 pack-unknown-atom

A pack names a capability atom the registry does not know.

## What it does

Fires once per unknown atom a pack references.

## Why it matters

An unknown atom can never match a use, so the rule that names it is silently dead.

## Remedy

Fix the atom name or add the atom to the registry.

## Examples

### Fires case 1

```pack expect=fire
issue unknown-atom a net.nope
```

### Clean case 2

```pack expect=clean
live a 1.0 t1
```
