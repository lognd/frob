<!-- mdtest: rule=UNITY003 -->
# UNITY003 duplicate-guid

Two or more tracked `.meta` files carry the same `guid`.

## What it does

With the opt-in `unity` pack enabled, every tracked `.meta` under `Assets/` (or an embedded package) is read for its `guid:` line, and a guid found in more than one file is an error naming every file. A `.meta` with no 32-hex guid is reported as unresolved, since it cannot be compared.

## Why it matters

Unity resolves references by guid; a duplicate makes references point at whichever asset it loads first.

## Remedy

Delete one of the assets together with its `.meta` and let Unity regenerate the copy, or copy it through the editor.

## Examples

### A violating case fires

The corpus runner writes a copy of the block as `Assets/Dup.cs.meta`, so two files share the guid.

```yaml expect=fire file=Assets/A.cs.meta
fileFormatVersion: 2 # error: UNITY003
guid: 0123456789abcdef0123456789abcdef
```

### A malformed guid is unresolved

```yaml expect=unresolved file=Assets/B.cs.meta
fileFormatVersion: 2 # unresolved: UNITY003
guid: not-a-guid
```

### A conforming case is clean

```yaml expect=clean file=docs/Notes.meta
fileFormatVersion: 2
guid: 0123456789abcdef0123456789abcdef
```
