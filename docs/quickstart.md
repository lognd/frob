# frob quickstart

A practical guide for a new user.

---

## 1. Installation

Using uv (recommended):

```bash
uv tool install frob
```

Using pip:

```bash
pip install frob
```

Verify the install:

```bash
frob --help
```

---

## 2. Orient a new project

The first two commands to run when you land in an unfamiliar codebase.

**Map the structure** -- shows every file, its line count, and top-level symbols:

```bash
frob map src/
```

Limit depth to get a high-level view:

```bash
frob map src/ --depth 2
```

**Outline a specific file** -- shows symbols with line numbers, no bodies:

```bash
frob outline src/frob/stub/__init__.py
```

JSON output for programmatic use:

```bash
frob outline src/frob/app/config.py --json
```

---

## 3. Core agentic loop

The typical pattern when using frob to drive an agent (Claude or otherwise):

```
frob map      -- what is here?
frob outline  -- what is in this file?
frob xref     -- what uses this symbol?
frob bundle   -- assemble context for the agent
[agent]       -- agent produces output / patch
frob parse    -- compress tool output before feeding back
```

---

## 4. Each command

### frob map

Emit a whole-project structural map in ~200 tokens.

```bash
frob map .
```

### frob outline

List top-level symbols in a file (functions, classes, methods).

```bash
frob outline src/frob/cycle/graph.py
```

### frob xref

Find all references to a symbol across a directory tree.

```bash
frob xref stub_file src/
```

Restrict to a specific language:

```bash
frob xref render_project src/ --lang python
```

### frob tokens

Estimate token cost of one or more files before putting them in context.

```bash
frob tokens src/frob/app/config.py src/frob/app/app.py
```

Detailed breakdown per file:

```bash
frob tokens src/ --detail
```

### frob bundle

Assemble the minimal context to implement or review a single function.
The focus file is stubbed to the target; local imports are reduced to signatures.

```bash
frob bundle src/frob/stub/__init__.py stub_file
```

Inline two levels of local imports:

```bash
frob bundle src/frob/stub/__init__.py stub_file --depth 2 > /tmp/context.md
```

### frob cycle

Detect import/include dependency cycles.

```bash
frob cycle src/ --lang python
```

Get suggestions for how to break each cycle:

```bash
frob cycle src/ --lang python --suggest
```

### frob stub

Reduce a source file to the function of interest (everything else becomes `...`).

```bash
frob stub src/frob/stub/__init__.py stub_file
```

Write the result to a file:

```bash
frob stub src/frob/stub/__init__.py stub_file -o /tmp/stub_file.py
```

### frob dup

Find duplicate or near-duplicate code blocks.

```bash
frob dup src/
```

Raise the minimum block size (default: 6 lines):

```bash
frob dup src/ --min-lines 10
```

### frob arch

Identify architectural warnings: oversized functions, classes with too many
methods, and similar structural issues.

```bash
frob arch src/
```

Tune thresholds:

```bash
frob arch src/ --max-function-lines 50 --max-class-methods 20
```

### frob parse

Compress raw tool output into a compact summary.

```bash
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
```

### frob init

Scaffold a new project from a registered template. See section 7 for details.

```bash
frob init list
frob init new python-library mylib --output ~/projects/mylib
```

---

## 5. Running tools and reading results

Raw tool output is noisy. `frob parse` compresses it before feeding it back
to an agent or reading it yourself.

**Supported tools:** pytest, ruff, ty, clang, clang++, gcc, g++, junit/gtest/catch2

Run pytest and get a compact summary:

```bash
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
```

Run ruff and get structured output:

```bash
ruff check src/ --output-format json 2>&1 | frob parse ruff
```

Run a C++ build and summarize compiler errors:

```bash
cmake --build build 2>&1 | frob parse clang --exit-code $?
```

In a CI pipeline, propagate failures:

```bash
pytest tests/ 2>&1 | frob parse pytest --exit-code $? --passthrough || exit 1
```

JSON output for programmatic use:

```bash
pytest tests/ 2>&1 | frob parse pytest --exit-code $? --json
```

---

## 6. Duplicate and architectural analysis

Use `frob dup` and `frob arch` together to find structural problems before
asking an agent to refactor.

Find duplicate blocks:

```bash
frob dup src/ --min-lines 8 --json > /tmp/dups.json
```

Find architecture warnings:

```bash
frob arch src/ --json > /tmp/arch.json
```

Then bundle the worst offender for a refactor agent:

```bash
frob bundle src/frob/app/config.py AppConfig --depth 2 > /tmp/context.md
```

---

## 7. Starting a new project

List available project types:

```bash
frob init list
```

Available types: python-library, python-tool, cpp-library, cpp-tool

Scaffold a Python library:

```bash
frob init new python-library mylib --output ~/projects/mylib
```

Scaffold a C++ executable:

```bash
frob init new cpp-tool mycli --output ~/projects/mycli
```

Scaffold a C++ library:

```bash
frob init new cpp-library myengine --output ~/projects/myengine
```

The generated C++ layout:

```
myengine/
  CMakeLists.txt
  README.md
  .gitignore
  src/
    myengine.cpp
  include/
    myengine.h
  tests/
    CMakeLists.txt
    test_myengine.cpp
```

Build a freshly scaffolded C++ project:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
cd build && ctest --output-on-failure
```

Use `--force` to overwrite an existing directory:

```bash
frob init new cpp-tool mycli --output ~/projects/mycli --force
```

---

## Configuration

frob reads `[tool.frob]` from `pyproject.toml` in the working directory.
CLI flags always override file config. Example:

```toml
[tool.frob]
map_depth = 3
dup_min_lines = 8
```
