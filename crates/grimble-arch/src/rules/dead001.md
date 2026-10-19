<!-- mdtest: rule=DEAD001 -->
# DEAD001 arch-dead-unit

A private function or method that nothing references.

## What it does

Fires for a function or method that is not public API, is not `main`, a test or a trait implementation, and has no call, reference or import edge from outside itself. May edges are respected: a unit reached only through a May edge, or whose name an unresolved call spells, is Unresolved, never dead. Types are not judged, since the graph has no edge for a use in a type position.

## Why it matters

Code nothing reaches still has to be read, kept compiling and kept secure.

## Remedy

Delete the unit, or use it.

## Examples

### Fires case 1

```rust expect=fire file=src/lib.rs
pub fn api() {}

fn unused() {}
```

### Clean case 2

```rust expect=clean file=src/lib.rs
pub fn api() {
    used();
}

fn used() {}
```

### Unresolved case 3

```python expect=unresolved file=src/m.py
class A:
    def _hook(self):
        pass

class B:
    def _hook(self):
        pass

def run(x):
    x._hook()
```
