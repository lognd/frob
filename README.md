# frob

Developer workflow CLI tools. Designed for agentic and human use.

Install: `pip install -e ~/Projects/Personal/frob` (editable) or `uvx frob`.

---

## Commands

### `frob init` -- project scaffolding

```bash
frob init list                              # list registered project types
frob init new <type> <name> --output DIR   # scaffold a new project
```

Project types:
- `python-library` -- installable Python package with logging, tests, CI
- `python-tool` -- Python CLI tool with argparse, app/, config, CI
- `cpp-library` -- FetchContent-compatible C++ library with CMake, GTest/Catch2, CI
- `cpp-tool` -- C++ executable with CMake, cross-platform CI, release workflow
- `pybind11-library` -- hybrid Python/C++ library using pybind11 + scikit-build-core
- `pyo3-library` -- hybrid Python/Rust library using PyO3 + maturin

All templates include: Makefile, .gitignore, docs/, GitHub Actions CI, branch-protection workflow.

---

### `frob map` -- project structure

```bash
frob map src/           # directory tree with token counts per file
frob map src/ --json    # JSON with path, lines, tokens, symbols per file
frob map src/ --depth 2 # limit recursion depth
```

---

### `frob outline` -- file signatures

```bash
frob outline src/file.py           # functions and classes with line numbers
frob outline src/file.py --json    # structured JSON output
```

Shows signatures only -- no bodies. Fast way to see what is in a file before reading it.

---

### `frob stub` -- single-function context

```bash
frob stub src/file.py target_fn              # keep target intact, stub everything else
frob stub src/file.py MyClass.method         # class method variant
frob stub src/file.py target_fn --output FILE
```

Useful for giving an LLM minimal context for one function.

---

### `frob bundle` -- function + its dependencies

```bash
frob bundle src/file.py fn_name         # function + all functions it calls
frob bundle src/file.py fn_name --depth 2
frob bundle src/file.py fn_name --format json
```

---

### `frob tokens` -- token count

```bash
frob tokens src/file.py            # total tokens
frob tokens src/file.py --detail   # per-symbol breakdown
frob tokens src/ --json            # JSON with total_tokens and per-file list
```

---

### `frob xref` -- cross-references

```bash
frob xref symbol src/       # find definition + all callers of a symbol
frob xref symbol src/ --json
```

---

### `frob cycle` -- import cycle detection

```bash
frob cycle src/             # detect import cycles
frob cycle src/ --suggest   # with refactoring suggestions
```

---

### `frob dup` -- duplicate code detection

```bash
frob dup src/                       # find structurally identical code blocks
frob dup src/ --min-lines 10        # minimum block size
frob dup src/ --json                # JSON with groups, clone_type, fragments
```

Detects exact clones and renamed-variable clones.

---

### `frob arch` -- architectural lint

```bash
frob arch src/                              # god-class, long-function, deep-nesting
frob arch src/ --json                       # JSON with suggestions list
frob arch src/ --max-function-lines 50
frob arch src/ --max-class-methods 20
```

---

### `frob docs` -- docstrings and docs/ search

```bash
frob docs src/file.py                       # extract all docstrings
frob docs src/file.py MyClass               # docstrings for a specific symbol
frob docs src/file.py --overview            # relevant headings from docs/ folder
frob docs src/ --search "authentication"    # full-text search through docs/ .md files
frob docs src/file.py --json
```

---

### `frob bind` -- binding consistency check

```bash
frob bind .                    # verify // BIND: comments match source declarations
frob bind . --json             # JSON with ok, mismatches list
frob bind . --list-bindings    # show all BIND declarations found
frob bind . --list-sources     # show all detected source signatures
```

Checks pybind11 (`bindings.cpp`) and PyO3 (`lib.rs`) `// BIND: signature` comments
against actual C++ header declarations and Rust `#[pyfunction]` signatures.

---

### `frob parse` -- parse tool output

```bash
<tool> | frob parse <tool>          # parse and summarize
<tool> | frob parse <tool> --json   # structured JSON
<tool> | frob parse <tool> --passthrough   # propagate exit code
```

Supported tools: `pytest`, `ruff`, `ty`, `clang`, `junit`, `pycharm`

---

### `frob inspect` -- PyCharm headless inspection

```bash
frob inspect <project_dir>
frob inspect <project_dir> --json
```

---

## Development

```bash
make install      # uv sync --all-extras
make format       # black + ruff format
make lint         # ruff + ty check
make test         # pytest tests/
make test-fast    # pytest --testmon (incremental)
make sync-skills  # sync skills/ and agents/ to ~/.claude (matching names only)
make upload       # bump version if needed, build wheel, publish to PyPI
make clean
```

## Skills and agents

The `skills/` and `agents/` directories contain Claude Code skill and agent definitions.
They are gitignored (local only). To sync them to `~/.claude`:

```bash
make sync-skills   # copies matching skills/agents to ~/.claude -- never creates new entries
```

The `.frob-foundation.md` convention: when `smart-start` generates infrastructure code,
it writes a registry of abstractions to `.frob-foundation.md` at the project root.
The `implementer` agent reads this file automatically so it knows which base classes,
protocols, and helpers already exist and should be used.
