# Agentic Workflow Guide

How to use frob tools together when acting as an orchestrator dispatching
subagents (e.g., Haiku for code generation, Sonnet for review).

---

## The full tool inventory

| Command | Purpose | Typical token cost |
|---------|---------|-------------------|
| `frob map` | Whole-project symbol map | ~150-300 |
| `frob outline` | File skeleton (functions, classes, line numbers) | ~30-80 |
| `frob tokens` | Estimate cost of reading a file | ~10 |
| `frob stub` | Keep one function, stub everything else | 20-50% of full file |
| `frob bundle` | Stubbed file + import signatures, ready for subagent | ~200-800 |
| `frob xref` | Definition site + all call sites for a symbol | ~50-150 |
| `frob cycle` | Detect import cycles, suggest fixes | ~20-100 |
| `frob parse` | Compress tool output (pytest/ruff/ty/clang) to ~5 lines | ~5-20 |
| `frob init` | Scaffold a new project | one-shot |

---

## Core loop: orient -> investigate -> change -> verify

```
map -> outline -> (stub | bundle) -> [implement / subagent] -> patch -> parse -> xref
```

### 1. Orient (map)

Start every session by mapping the project:

```
frob map src/
```

Gives you the full symbol inventory in ~200 tokens. Identify which files are
relevant before reading anything.

### 2. Investigate (outline + tokens + stub)

For each relevant file, get its structure and cost before deciding how to read:

```
frob outline src/frob/stub/__init__.py
frob tokens src/frob/stub/__init__.py src/frob/ast/python.py
```

Then choose a reading strategy:

| File size | Strategy |
|-----------|---------|
| < 200 tokens | Read in full |
| 200-800 tokens | `frob stub <file> <nearby_function>` to get context around area of interest |
| > 800 tokens | `frob bundle <file> <target>` for subagent dispatch |

`frob stub` is especially useful for understanding the structure around a
function without reading the whole file:

```
# Read just the area around _emit_py, stub everything else
frob stub src/frob/stub/__init__.py _emit_py
```

### 3. Understand impact (xref + cycle)

Before changing anything, know the blast radius:

```
frob xref stub_file src/           # who calls this?
frob cycle src/ --suggest          # will my change create a cycle?
```

### 4. Dispatch a subagent (bundle)

Assemble minimal context and send to a Haiku agent:

```
frob bundle src/frob/stub/__init__.py stub_file --format markdown
```

Paste the output as the subagent's context, followed by your instruction.
The agent sees exactly what it needs -- the stubbed file showing where the
function fits + signatures of everything it can call -- and nothing more.

**Subagent prompt template (implementation):**
```
You are implementing a single function. Here is the context:

{frob bundle output}

Task: implement `{target}` so that {description}.

Constraints:
- Only change the body of `{target}`. Do not touch other functions.
- Return ONLY a unified diff. Do not explain. Do not include anything outside the diff.
```

**Subagent prompt template (tests):**
```
You are writing pytest tests for a single function. Here is the context:

{frob bundle output}

Task: write tests for `{target}` covering: {cases}.

- Add tests to tests/{test_file}.py.
- Return ONLY a unified diff.
```

### 5. Apply the result (patch)

The subagent returns a unified diff:

```
frob patch --check /tmp/agent_output.diff   # validate first
frob patch /tmp/agent_output.diff           # apply
```

### 6. Verify (parse + outline + xref)

```
# Run tools, get compact summaries
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
ruff check src/ --output-format json | frob parse ruff
ty check src/ 2>&1 | frob parse ty

# Confirm structure matches intent
frob outline src/frob/stub/__init__.py

# Confirm callers still compatible
frob xref stub_file src/
```

---

## Token budget reference

| Operation | Typical cost |
|-----------|-------------|
| `frob map src/` | ~150-300 tokens |
| `frob outline <file>` | ~30-80 tokens |
| `frob tokens <file>` | ~10 tokens |
| `frob stub <file> <target>` | 20-50% of raw file |
| `frob bundle <file> <target>` | ~200-800 tokens |
| `frob xref <symbol> src/` | ~50-150 tokens |
| `frob parse pytest` (150-test run) | ~10-20 tokens |
| `frob parse ruff` | ~5-30 tokens |
| Reading a file directly | 300-5,000+ tokens |

---

## Haiku vs Sonnet allocation

| Task | Agent |
|------|-------|
| Implement a well-scoped function with clear types | Haiku |
| Write tests for a function given its signature | Haiku |
| Debug a single failing test | Haiku |
| Parse/transform a known format | Haiku |
| Design a new module or protocol | Sonnet (you) |
| Review a Haiku agent's output for correctness | Sonnet (you) |
| Refactor across multiple files | Sonnet (you) |
| Architecture decisions | Sonnet (you) |
| Anything requiring xref/cycle awareness | Sonnet (you) |

---

## Example: full agentic session

```bash
# 1. Orient
frob map src/frob/

# 2. Pick a target
frob outline src/frob/bundle/__init__.py
frob tokens src/frob/bundle/__init__.py src/frob/stub/__init__.py

# 3. Check blast radius
frob xref build_bundle src/

# 4. Assemble context for Haiku
frob bundle src/frob/bundle/__init__.py build_bundle --depth 2 > /tmp/ctx.md

# 5. [Haiku agent implements or fixes build_bundle]
# ... haiku produces /tmp/fix.diff ...

# 6. Apply
frob patch --check /tmp/fix.diff
frob patch /tmp/fix.diff

# 7. Verify
pytest tests/test_bundle.py --tb=short 2>&1 | frob parse pytest --exit-code $?
ty check src/ 2>&1 | frob parse ty
ruff check src/ --output-format json | frob parse ruff
```
