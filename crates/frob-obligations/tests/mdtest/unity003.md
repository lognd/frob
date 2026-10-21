<!-- mdtest: rule=UNITY003 -->
# UNITY003

## A violating case fires

The corpus runner writes a copy of the block as `Assets/Dup.cs.meta`, so two files share the guid.

```yaml expect=fire file=Assets/A.cs.meta
fileFormatVersion: 2 # error: UNITY003
guid: 0123456789abcdef0123456789abcdef
```

## A malformed guid is unresolved

```yaml expect=unresolved file=Assets/B.cs.meta
fileFormatVersion: 2 # unresolved: UNITY003
guid: not-a-guid
```

## A conforming case is clean

```yaml expect=clean file=docs/Notes.meta
fileFormatVersion: 2
guid: 0123456789abcdef0123456789abcdef
```
