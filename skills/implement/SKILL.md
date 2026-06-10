---
name: implement
description: Implement stubbed functions by dispatching Haiku agents per function. Use after stubs and tests exist. Use when the user says "implement X", "fill in X", or as part of the develop pipeline.
---

# implement

Fill in `...` bodies one function at a time, using Haiku agents.
Never implement more than one function per agent dispatch.

## Prerequisites

Before dispatching any agent:
1. Stubs exist (all function signatures defined, bodies are `...`)
2. Tests exist and collect without errors (they may fail -- that is expected)
3. `frob cycle src/` is clean

## Process per function

### 1. Get context

```bash
frob bundle src/frob/<module>/__init__.py <function_name> --depth 2 > /tmp/ctx.md
frob tokens /tmp/ctx.md
```

If `/tmp/ctx.md` is >800 tokens, reduce depth:

```bash
frob bundle src/frob/<module>/__init__.py <function_name> --depth 1 > /tmp/ctx.md
```

### 2. Check what calls this function

```bash
frob xref <function_name> src/
```

If callers exist, note their expectations in the agent prompt.

### 3. Dispatch implementer agent

Use the `implementer` agent (see `agents/implementer/SKILL.md`):

```
You are implementing a single function. Context:

{contents of /tmp/ctx.md}

Task: implement `{function_name}` so that {one sentence description of what it should do}.

Callers expect: {note any constraints from xref output, or "none yet"}

Constraints:
- Use typani Result[T, E] for error returns. Never raise.
- Use pydantic BaseModel for any structured data.
- Use frob.logging.get_logger(__name__) for any debug output.
- Return ONLY a unified diff. No prose.
```

### 4. Validate and apply

```bash
git apply --check /tmp/impl.diff
git apply /tmp/impl.diff
```

If `--check` fails, read the diff and fix manually, or re-dispatch with the error.

### 5. Run tests immediately

```bash
pytest tests/test_{module}.py -x --tb=short 2>&1 | frob parse pytest --exit-code $?
```

If new failures appear, run `/fix` on just this function before moving on.
Never accumulate multiple broken functions.

## Order of implementation

Implement in dependency order -- lower-level helpers before the functions that call them.

Read `frob outline src/frob/<module>/__init__.py` to see the call graph implied by
the import structure. Implement leaf functions first.

## When NOT to dispatch to Haiku

- The function requires reading multiple files to understand (use Sonnet -- yourself)
- The function involves a new algorithm or data structure design (use `/plan` first)
- The function requires xref/cycle awareness across the whole project
- The diff from the last agent was completely wrong (redesign the stub instead)

## Batch mode (for simple functions)

For trivial functions (<5 lines each), you may implement them yourself inline
rather than dispatching. The overhead of dispatch is not worth it for:
- Property accessors
- Simple format conversions
- Pass-through wrappers
- `__repr__` / `__str__`

## After all functions implemented

```bash
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
ty check src/ 2>&1 | frob parse ty
ruff check src/ --output-format json | frob parse ruff
frob cycle src/
```

All must be clean before moving to `/document`.
