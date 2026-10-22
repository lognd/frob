<!-- mdtest: rule=LNK001 -->
# Cross-file links

## Fires on a missing file

```markdown expect=fire
[gone](missing.md) <!-- error: LNK001 -->
```

## Clean when the linked file is another block of the case

```markdown expect=clean
[it](other.md) and [deep](docs/b.md)
```

```markdown file=other.md
# Other
```

```markdown file=docs/b.md
# B
```

## Fires in a second file of a mixed-language case

```markdown expect=fire fidelity=F3
[it](other.md)
```

```markdown file=other.md
# Other
```

```rust file=src/a.rs fidelity=F1
let broken = 1; // error: LNK001
```
