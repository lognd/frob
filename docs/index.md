# frob

Developer workflow CLI. Token-efficient tools for agentic and human-driven development.

## Command reference

### Context and navigation

| Command | Purpose | Typical tokens |
|---------|---------|---------------|
| `frob map src/` | Whole-project symbol map | 150-300 |
| `frob outline FILE` | File skeleton: signatures + line numbers | 30-80 |
| `frob tokens FILE` | Estimate read cost before reading | ~10 |
| `frob stub FILE SYMBOL` | One function in focus, rest stubbed | 20-50% of file |
| `frob bundle FILE SYMBOL` | Function + full import dependency tree | 200-800 |
| `frob ctx FILE SYMBOL` | Adaptive: auto-picks stub/bundle/full by complexity | 20-800 |
| `frob xref SYMBOL src/` | Definition site + every call site | 50-150 |
| `frob docs FILE` | Extract docstrings (`--search Q`, `--overview`) | 20-100 |

### Analysis

| Command | Purpose |
|---------|---------|
| `frob cycle src/` | Detect import cycles |
| `frob dup src/` | Find duplicate code blocks |
| `frob arch src/` | Architectural lint: long functions, god classes, coupling |
| `frob bind .` | Verify pybind11/PyO3 BIND declaration coverage |
| `frob exports src/pkg/` | Generate `__init__.py` from public symbols |
| `frob inspect <project>` | PyCharm headless inspection (auto-located) |

### Editing (staging model)

| Command | Purpose |
|---------|---------|
| `frob edit FILE SYMBOL` | Read-only: show source + line range |
| `frob edit FILE SYMBOL --stage` | Stage replacement from stdin (no lock; concurrent-safe) |
| `frob edit FILE --commit` | Apply all staged patches atomically |
| `frob edit FILE --status` | Show pending staged patches |
| `frob edit FILE SYMBOL --immediate` | Lock + write now (single-agent only) |

### Validation

| Command | Purpose |
|---------|---------|
| `frob check src/` | Aggregate: ruff + ty + cycle + dup + arch + bind + exports |
| `frob check src/ --type cpp` | C++: cmake + clang-tidy + clang-format + ctest |
| `frob check src/ --type rust` | Rust: cargo check + clippy + fmt + test |
| `frob parse TOOL` | Parse pytest/ruff/ty/cargo/clang-tidy/valgrind output |

### Scaffolding

| Command | Purpose |
|---------|---------|
| `frob scaffold list` | List available project templates |
| `frob scaffold new TYPE NAME` | Scaffold a new project |

### Coordination (orchestrator)

| Command | Purpose |
|---------|---------|
| `frob mission new TYPE` | Create agent briefing in `.frob/missions/` |
| `frob mission done ID` | Mark complete, delete briefing |
| `frob mission stuck ID REASON` | Escalate blocker, move to `stuck/` |
| `frob mission list` | Show pending missions |
| `frob dispatch create LABEL` | Create isolated git worktree on fresh branch |
| `frob dispatch collect ID` | Rebase + fast-forward merge completed branch |
| `frob dispatch abort ID` | Discard worktree + branch |
| `frob dispatch list` | Show active dispatches |
| `frob todo add TEXT` | Add cross-session TODO item |
| `frob todo done ID` / `remove ID` | Complete or remove |
| `frob todo list [--all]` | List pending (or all) items |
| `frob gitlog [--level LEVEL]` | Summarize git history by conventional commit type |

## Architecture

```
src/frob/
  __main__.py          -- CLI entry (argparse)
  app/
    app.py             -- App: dispatches subcommands
    config.py          -- AppConfig: merges CLI args + pyproject.toml [tool.frob]
    *_runner.py        -- One runner per subcommand
  ast/
    common.py          -- Shared protocols for tree-sitter adapters
    python.py          -- Python grammar adapter
    cpp.py             -- C++ grammar adapter
  map/                 -- Project structure map
  outline/             -- File skeleton emitter
  stub/                -- Single-function focus
  bundle/              -- Function + import tree assembler
  ctx/                 -- Adaptive context tier selector
  xref/                -- Symbol cross-reference
  edit/                -- Symbol-level editor with staging
  exports/             -- __init__.py generator
  cycle/               -- Import cycle detection (Tarjan SCC)
  dup/                 -- Duplicate block detection
  arch/                -- Architectural lint
  docs/                -- Docstring extractor
  bind/                -- pybind11/PyO3 BIND verification
  inspect/             -- PyCharm headless inspection
  check/               -- Aggregate quality gate
  scaffold/            -- Project templater
  mission/             -- Agent briefing system
  dispatch/            -- Git worktree isolation
  todo/                -- Cross-session TODO tracker
  gitlog/              -- Git history summarizer
  process/
    parsers/           -- pytest, ruff, ty, cargo, clang-tidy, valgrind parsers
  logging/             -- Structured logging setup
```

## Configuration

`[tool.frob]` in `pyproject.toml`. CLI flags override file config.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic>=2.12` | Config models and all structured return types |
| `typani>=0.0.3` | `Result`, `Option`, `ErrorSet` for explicit error handling |
| `tree-sitter>=0.25` | Incremental parser runtime |
| `tree-sitter-python>=0.25` | Python grammar |
| `tree-sitter-cpp>=0.23` | C/C++ grammar |
| `jinja2>=3.1` | Template rendering for scaffold |
