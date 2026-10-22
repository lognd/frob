<!-- mdtest: rule=CFG001 -->
# Root

```toml
strict = false
level = 1
```

## Child overrides the parent

```toml
strict = true
```

### Grandchild inherits both

#### Great-grandchild inherits through three levels

```text expect=fire
x // error: CFG001
```

## Sibling keeps the root value

```text expect=clean
x
```

## Inline config wins last

```text expect=clean config="strict = false"
x
```
