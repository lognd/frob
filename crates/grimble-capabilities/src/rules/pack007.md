<!-- mdtest: rule=PACK007 -->
# PACK007 pack-unknown-infer-rule

A pack names an inference rule that does not exist.

## What it does

Fires once per unknown infer rule a pack names.

## Why it matters

The inference never runs.

## Remedy

Fix the rule name.

## Examples

### Fires case 1

```pack expect=fire
issue unknown-infer-rule a infer.nope
```

### Clean case 2

```pack expect=clean
live a 1.0 t1
```
