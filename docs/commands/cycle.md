# frob cycle

Detect and explain dependency cycles in a codebase.

## Usage

```
frob cycle <path> [--lang python|cpp] [--suggest]
```

`<path>` is a file or directory. When a directory is given, all recognized source
files under it are scanned recursively.

`--suggest` prints refactoring hints for each cycle found.

## Detection algorithm

Imports/includes are extracted via tree-sitter, then a directed dependency graph
is built where each node is a module (file). Tarjan's SCC algorithm finds all
strongly connected components with more than one node -- those are cycles.

For each cycle the tool prints:

```
Cycle (3 nodes):
  src/foo.py  ->  src/bar.py  ->  src/baz.py  ->  src/foo.py
```

## Suggestions (`--suggest`)

For each cycle frob attempts one of the following fixes, in priority order:

1. **Extract shared primitives** -- if a symbol used in both directions is a
   simple data class or constant, suggest moving it to a new module.
2. **Invert dependency via protocol** -- if one direction is a concrete call,
   suggest introducing a `Protocol` / abstract base to break the link.
3. **Merge modules** -- if the cycle is tight and both modules are small,
   suggest collapsing them.

## Language support

| Language | Import extraction |
|----------|------------------|
| Python | `import`, `from ... import` via tree-sitter-python |
| C/C++ | `#include` directives via tree-sitter-cpp |

## Error handling

Returns `Result[list[Cycle], CycleError]`:

- `CycleError.ParseFailed` -- tree-sitter could not parse a file
- `CycleError.UnsupportedLanguage` -- no adapter registered for detected language
