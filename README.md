# frob

Developer workflow CLI tools. Designed for agentic and human use.

Install: `pip install frob` or `uvx frob`. For editable dev install: `pip install -e .`

---

## Commands

| Command | Description |
|---------|-------------|
| `frob map` | Recursive directory tree with file sizes and line counts |
| `frob outline` | Structural skeleton of a file: classes, functions, signatures, line numbers |
| `frob xref` | Find where a symbol is defined and every file that references it |
| `frob tokens` | Estimate token cost of files before reading them |
| `frob bundle` | Assemble minimal context for a function as a subagent prompt |
| `frob ctx` | Adaptive context: auto-selects stub/bundle/full based on complexity |
| `frob stub` | Reduce a file to one or more targets, stubbing everything else |
| `frob exports` | Generate a ready-to-paste `__init__.py` from all public symbols |
| `frob check` | Aggregate quality gate: ruff, ty, cycle, dup, arch, bind, exports |
| `frob cycle` | Detect import cycles in Python packages |
| `frob gitlog` | Summarize git history filtered by conventional commit type |
| `frob edit` | Isolate, stage, and atomically commit changes to a single symbol |
| `frob dispatch` | Decompose a task into parallel agent missions |
| `frob mission` | Manage individual agent mission state |
| `frob todo` | Lightweight task list stored in `.frob/` |

See `docs/` for detailed documentation on each command.
