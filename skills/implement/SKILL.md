---
name: implement
description: Implement stubbed functions by dispatching Haiku agents one function at a time. Use after stubs and tests exist. Emphasizes verify-after-each-function with the fast single-test loop.
---

# implement

Fill `...` bodies one function at a time. Verify after each one before moving on.
Never accumulate multiple unverified implementations.

## Prerequisites

1. Stubs exist (all signatures written, bodies are `...` or equivalent)
2. Tests collect without errors (they fail -- that is expected)
3. No import cycles

## Process per function

### 1. Get context (minimal)

**If using frob:**
```bash
frob bundle src/<module>/__init__.py <function_name> --depth 2 > /tmp/ctx.md
frob tokens /tmp/ctx.md   # if >800 tokens, reduce depth to 1
```

**Load foundation registry (always do this if the file exists):**
```bash
# Check for foundation registry at project root
if [ -f .frob-foundation.md ]; then
    echo "=== Foundation Registry ===" >> /tmp/ctx.md
    cat .frob-foundation.md >> /tmp/ctx.md
    # For each file listed in the registry, append its outline
    # so the implementer sees full signatures without reading bodies
    frob outline src/<project>/_infra.py >> /tmp/ctx.md 2>/dev/null || true
fi
```

Include the foundation content verbatim in the agent prompt under a `Foundation Registry` heading.
The implementer agent will use it to choose the right abstractions rather than re-implementing them.

**Otherwise (read the function + what it calls):**
```bash
grep -n -A 30 "^def <function_name>\|^    def <function_name>" src/<module>/<file>.py
```

### 2. Check callers

```bash
frob xref <function_name> src/        # if using frob
grep -rn "<function_name>" src/       # otherwise
```

Note any constraints callers impose (argument types, return shape).

### 3. Dispatch implementer agent (or implement directly)

**Dispatch when:** function body >10 lines, or has non-trivial logic.
**Implement directly when:** trivial (<5 lines), a property accessor, or a format conversion.

Agent prompt template:
```
You are implementing a single function. Context:

{frob bundle output, or relevant code excerpts}

Task: implement `{function_name}` so that {one sentence what it does}.

Callers expect: {note from xref, or "none yet"}

Language: {Python/C++}

For Python:
- Use typani Result[T, E] for fallible returns. Never raise at module boundary.
  Ok(value) for success, Err(SomeError.Variant) for failure.
  All Result/Option accessors are properties, never methods: .is_ok, .is_err,
  .danger_ok, .danger_err, .ok, .err (safe). Chain with | (map) or >> (and_then).
- Use pydantic BaseModel for structured data.
- Use get_logger(__name__) for debug output. No print().

Output ONLY the new function source. No diff markers. No prose.
```

### 4. Apply

```bash
# Agent output is raw function source -- pipe directly to frob edit
echo "$impl_output" | frob edit src/<module>/<file>.py <function_name> --immediate
```

If the output starts with `BLOCKER:` or `ERROR:`: do not apply.

**If the agent returned BLOCKER:**
- Bypass permissions OFF: surface BLOCKER + SUGGESTION to user verbatim, wait for decision.
- Bypass permissions ON: dispatch /oracle with the BLOCKER as the question, apply the DECISION,
  resume. Log "BLOCKER resolved via oracle: {DECISION}" for later review.
Never patch around a BLOCKER either way.

### 5. Verify with SINGLE test (fast loop)

```bash
pytest tests/test_<module>.py -k "<function_name>" -x --tb=short
```

If that passes, also run the full module test file:
```bash
pytest tests/test_<module>.py --tb=short
```

Only after module tests pass: move to the next function.

**NEVER** run the full test suite after each individual function -- too slow.
Run the full suite once after ALL functions in a module are implemented.

## Implementation order

Implement dependency-first (leaf functions before callers):

```bash
frob outline src/<module>/__init__.py   # see call structure
```

Or read imports: functions that import nothing from the same module can be implemented first.

## When NOT to dispatch to Haiku

- Function requires reading multiple files to understand (implement yourself)
- Function involves a new algorithm or data structure not in the stubs (run /plan first)
- Function requires cross-file xref awareness (implement yourself)
- Last agent for this function returned a wrong diff (implement yourself, don't re-dispatch)
- Agent returned BLOCKER (surface to user, resolve design issue first)

## After all functions in a module implemented

```bash
pytest tests/test_<module>.py -q                  # module tests
pytest tests/test_integration_*.py -q             # integration tests if they exist
```

Fix any failures with /fix before moving to the next module.

## After ALL modules implemented

```bash
pytest tests/ -q                    # full suite
ty check src/ 2>&1 | head -30       # type check (Python)
ruff check src/ --output-format json | head  # lint (Python)
frob cycle src/                     # if using frob: check for cycles
```

All must be clean before /document.
