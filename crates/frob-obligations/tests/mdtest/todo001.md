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

## Unresolved for a file type no scanner reads

The rule cannot examine an opaque text file, so it says so instead of passing.

```text expect=unresolved file=notes.xyz
TODO this file is never scanned
```

## Language matrix

One bare-marker case per matrix cell (docs/design/testing.md section 4). The expected class
of each cell is derived from the rule's needs and the capability matrix, and a block that
contradicts it fails the matrix check; `parity=bare` ties the examined cells to one outcome.

```rust expect=fire cell=rust parity=bare file=src/lib.rs
// TODO tidy this // error: TODO001
fn a() {}
```

```python expect=fire cell=python parity=bare file=app.py
# TODO tidy this # error: TODO001
def a():
    pass
```

```typescript expect=fire cell=typescript parity=bare file=app.ts
// TODO tidy this // error: TODO001
function a() {}
```

```csharp expect=fire cell=csharp parity=bare file=App.cs
// TODO tidy this // error: TODO001
class A {}
```

```markdown expect=fire cell=markdown parity=bare file=notes.md
# Title

<!-- TODO tidy this --> <!-- error: TODO001 -->
```

```text expect=unresolved cell=text reason=fidelity file=notes.txt
TODO tidy this
```

```text expect=notapplicable cell=binary reason=binary file=logo.png
TODO tidy this
```

````markdown expect=fire cell=island file=notes.md
# Title

```text
TODO inside a fence is code, not a marker
```

<!-- TODO tidy this --> <!-- error: TODO001 -->
````
