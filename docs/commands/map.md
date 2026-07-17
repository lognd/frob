# frob map

Emit a whole-project structural map: every file, its line count, and its
top-level symbols. Fits an entire medium-sized codebase in ~200 tokens.

## Usage

```
frob map [path] [--json] [--depth N]
```

`path` defaults to the current directory. `--depth` limits directory recursion
(default: unlimited).

## Output (default)

```
src/frob  (12 files, 842 lines)
  __init__.py                 1L
  __main__.py                52L  _build_parser
  _compat.py                 16L  toml, Self
  app/
    app.py                   22L  App
    config.py                65L  Subcommand, AppConfig
    cycle_runner.py          52L  run
    init_runner.py           34L  run
    stub_runner.py           25L  run
  ast/
    common.py                43L  ModuleTag, ClassTag, FunctionTag, UsableByCycle
    python.py               195L  parse_file, parse_bytes, get_imports, emit_stub ...
    cpp.py                  160L  parse_file, parse_bytes, get_imports, emit_stub ...
  cycle/
    graph.py                 55L  DependencyGraph, find_cycles
  stub/
    __init__.py              52L  StubError, stub_file
```

## Why it exists

Claude's first move in any codebase is "what is here and where?". Without `map`,
that requires either reading every file or guessing paths. `map` answers the
planning question in a single tool call at minimal token cost.

## JSON output (`--json`)

Returns a tree of `FileNode` objects, each with `path`, `lines`, and `symbols`
(top-level names only). Machine-readable for subagent dispatch logic.
