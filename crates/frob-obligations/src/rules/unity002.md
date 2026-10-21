<!-- mdtest: rule=UNITY002 -->
# UNITY002 orphan-meta

A tracked `.meta` file whose asset is not tracked.

## What it does

With the opt-in `unity` pack enabled, a tracked `<asset>.meta` under `Assets/` (or an embedded package) must have its `<asset>` file or folder tracked too. Unity-ignored names are exempt. A folder `.meta` kept for an empty folder is an orphan, because git cannot track the empty folder. The finding names the `.meta`.

## Why it matters

An orphan `.meta` reserves a guid for an asset nobody has; Unity deletes it on the next import and the diff churns.

## Remedy

Delete the `.meta`, or track the missing asset.

## Examples

### A violating case fires

```yaml expect=fire file=Assets/Gone.cs.meta
fileFormatVersion: 2 # warn: UNITY002
guid: 0123456789abcdef0123456789abcdef
```

### A conforming case is clean

```yaml expect=clean file=docs/Notes.meta
fileFormatVersion: 2
guid: 0123456789abcdef0123456789abcdef
```
