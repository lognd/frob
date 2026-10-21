<!-- mdtest: rule=UNITY002 -->
# UNITY002

## A violating case fires

```yaml expect=fire file=Assets/Gone.cs.meta
fileFormatVersion: 2 # warn: UNITY002
guid: 0123456789abcdef0123456789abcdef
```

## A conforming case is clean

```yaml expect=clean file=docs/Notes.meta
fileFormatVersion: 2
guid: 0123456789abcdef0123456789abcdef
```
