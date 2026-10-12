<!-- mdtest: rule=TODO001 -->
<!-- frob:ticket 01M4FD3KT1XFB1N1GZYXFRMPT7 -->
# TODO001 bare work markers

## Fires on a bare marker in a block comment

```rust expect=fire
/* TODO tidy this */ // error: TODO001
fn a() {}
```

## Fires on each marker word

```rust expect=fire
// FIXME later // error: TODO001
// XXX revisit // error: TODO001
// HACK around it // error: TODO001
fn a() {}
```

## Fires in a markdown comment

```markdown expect=fire
# Title

<!-- TODO write this --> <!-- error: TODO001 -->
```

## Fires in a YAML comment

YAML and TOML comments are scanned like any other language's (docs/reference/fidelity.md).

```yaml expect=fire
# TODO tidy this # error: TODO001
name: ci
```

## Clean in a YAML comment owned by a todo directive

```yaml expect=clean
# frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 tidy
# TODO tidy this
name: ci
```

## Clean when a todo directive sits on the previous line

```rust expect=clean
/* frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 tidy */
/* TODO tidy this */
fn a() {}
```

## Clean when the id follows the marker in parentheses

```rust expect=clean
// TODO(01J9QKX3M8Z4T7N2V5B6C0D1E2): tidy this
fn a() {}
```

## Clean for lowercase words and strings

```rust expect=clean
// todo is fine in lowercase, and so is TODO001 as a rule id
fn a() -> &'static str { "TODO inside a string" }
```

## Clean inside a fenced block of markdown

````markdown expect=clean
# Title

```text
TODO this is code
```
````
