<!-- mdtest: rule=PACK006 -->
# PACK006 pack-unavailable

An enabled pack could not be loaded.

## What it does

Reports one Unresolved finding with reason `pack-unavailable` per enabled pack that cannot be loaded; it is required (fails the gate) when the pack is marked required. PACK001 does not evaluate such a pack. The corpus runner shows a required finding as an Error for the fire control, because the harness fire control rejects Unresolved findings.

## Why it matters

A pack that did not run must never read as a pass.

## Remedy

Make the pack loadable, or disable it.

## Examples

### Fires case 1

```pack expect=fire
unavailable a required
```

### Clean case 2

```pack expect=clean
live a 1.0 t1
```

### Unresolved case 3

```pack expect=unresolved reason=pack-unavailable
unavailable a
```
