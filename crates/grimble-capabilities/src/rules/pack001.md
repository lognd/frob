<!-- mdtest: rule=PACK001 -->
# PACK001 pack-lock-mismatch

An enabled pack differs from its lock entry.

## What it does

Fires once per pack-level difference and per item that is changed, added or removed since the lock was written, and once for an enabled pack with no lock entry (reason `lock-missing`). A pack that could not be loaded is skipped here and reported by PACK006.

## Why it matters

The lock is the reviewed record of what each pack does; a silent change to a pack changes what the checker enforces.

## Remedy

Review the pack change and re-lock with an explicit update, or revert the pack.

## Examples

### Fires case 1

```pack expect=fire
lock a 1.0 t1 k=d1
live a 1.0 t2 k=d2
```

### Clean case 2

```pack expect=clean
lock a 1.0 t1 k=d1
live a 1.0 t1 k=d1
```

### Fires case 3

```pack expect=fire
live a 1.0 t1 k=d1
```
