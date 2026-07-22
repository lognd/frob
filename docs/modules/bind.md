# frob bind

`frob.bind` verifies that `// BIND:` comment declarations in pybind11/PyO3
glue code have a matching function declaration on the native side, so a
Python-facing binding never silently drifts from the C++/Rust signature it
claims to wrap.

<!-- frob:invariant INV-007 -->

See `invariants/INV-007.md` for the formal invariant statement and its
evidence test ids.

## Usage

```
frob bind <path> [--json] [--list-bindings]
```

## Public API

<!-- frob:describes src/frob/bind/__init__.py::BindingDecl -->
<!-- frob:describes src/frob/bind/__init__.py::SourceDecl -->
<!-- frob:describes src/frob/bind/__init__.py::Mismatch -->
<!-- frob:describes src/frob/bind/__init__.py::scan_bindings -->
<!-- frob:describes src/frob/bind/__init__.py::scan_sources -->
<!-- frob:describes src/frob/bind/__init__.py::check -->

```python
# frob/bind/__init__.py
class BindingDecl
    # One `// BIND: <signature>` comment found in a .cpp/.rs file, tagged
    # pybind11 or pyo3 by which file type it came from.

class SourceDecl
    # One function declaration found on the native side (C++ header/impl
    # or a #[pyfunction]-annotated Rust fn) that a binding might match.

class Mismatch
    # A BindingDecl with no matching SourceDecl, plus a human-readable
    # reason string.

scan_bindings(root: Path) -> list[BindingDecl]
    # Walks `root` for `// BIND:` comments in .cpp and .rs files.

scan_sources(root: Path) -> list[SourceDecl]
    # Walks `root` for candidate native declarations: C++ header function
    # signatures and Rust #[pyfunction] definitions.

check(root: Path) -> list[Mismatch]
    # Cross-references scan_bindings() against scan_sources() by normalized
    # function name and reports every binding with no source match.
```
