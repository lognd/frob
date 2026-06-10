# frob

Developer workflow tools available under a single `frob` CLI.

## Subtools

| Command | Purpose |
|---------|---------|
| `frob init` | Project templater -- scaffold new projects from registered templates |
| `frob cycle` | Dependency cycle checker -- detect and explain import/include cycles |
| `frob stub` | Stub generator -- reduce a source file to the function of interest |

## Architecture

```
frob/
  __main__.py       -- CLI entry point (argparse)
  app/
    app.py          -- App: dispatches to subtool runners
    config.py       -- AppConfig: merges CLI args + optional config file (pydantic)
  ast/
    common.py       -- Shared protocols: UsableByCycle, UsableByStub, StubEmitter
    python.py       -- Python adapter (tree-sitter-python)
    cpp.py          -- C++ adapter (tree-sitter-cpp)
  cycle/
    graph.py        -- Dependency graph + Tarjan SCC cycle detection
  init/
    project.py      -- Template manifests + Jinja2 file renderer
    data/           -- .j2 template files
  stub/
    __init__.py     -- Stub orchestration: parse -> focus -> emit
```

## Configuration

`frob` looks for a `[tool.frob]` section in `pyproject.toml` in the working
directory. CLI flags always override file config.

## Dependencies

- `pydantic>=2.12` -- config models and validation
- `typani>=0.0.3` -- `Result`, `Option`, `ErrorSet` for explicit error handling
- `tree-sitter>=0.25` -- incremental parser runtime
- `tree-sitter-python>=0.25` -- Python grammar
- `tree-sitter-cpp>=0.23` -- C/C++ grammar
- `jinja2>=3.1` -- template rendering for `init`

## Adding a New Language

1. Create `src/frob/ast/<lang>.py` implementing `UsableByCycle` and/or `UsableByStub`.
2. Register the adapter in `app/config.py` under `LANGUAGE_ADAPTERS`.
3. Add template files under `init/data/` and a manifest entry in `init/project.py`.
