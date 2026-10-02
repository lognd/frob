<!-- mdtest: rule=MDT001 -->
# Toy rule

## fire with markers

```rust expect=fire
let a = 1;
let b = forbidden; // error: MDT001
let c = forbidden_too; // error: MDT001
```

## fire without markers

```py expect=fire
x = forbidden
```

## warn marker

```py expect=fire rule=MDT002
x = 1
y = forbidden  # warn: MDT002
```

## clean

```rust expect=clean
let ok = allowed;
```

<!-- mdtest: rule=MDT002 -->
# Second rule

```py expect=fire
y = forbidden  # warn: MDT002
```

```py expect=clean
y = fine
```
