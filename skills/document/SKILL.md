---
name: document
description: Write docstrings and update docs/ after implementation is complete. Use when the user says "document X", "add docs", or as the final step in the develop pipeline.
---

# document

Add docstrings and update docs/ to match the final implementation.
Docs describe WHAT and WHY. Never HOW (that is the code's job).

## Step 1: Find what needs docs

**If using frob:**
```bash
frob outline src/<module>/__init__.py
```

**Python without frob:**
```bash
grep -n "^def \|^    def \|^class " src/<module>/<file>.py
```

Look for public symbols (no leading underscore) without docstrings.

## Step 2: Write docstrings

**Rules:**
- One line for simple functions. Multi-line ONLY for non-obvious behavior.
- Describe what the function does from the CALLER's perspective.
- Include return semantics for fallible functions: "Returns Ok(X) on success, Err(E.Y) if Z."
- Do NOT describe parameters whose name and type are self-documenting.
- Do NOT reference the current task, issue number, or why it was added.
- No ASCII art. No parameter tables for simple functions.

**Python format:**
```python
def function_name(arg: Type) -> Result[X, E]:
    """Short description. Returns Ok(X) or Err(E.Reason) if condition."""
```

Multi-line only when there is a non-obvious constraint:
```python
def complex_function(arg: Type) -> Result[X, E]:
    """
    Short summary.

    Note: only works when X because Y. Call setup() first.
    """
```

**C++ format:**
```cpp
/// Brief description.
/// Returns false if condition.
bool function_name(Type arg);
```

## Step 3: Update design docs

For each doc in `docs/<feature>.md`:
- Update API signatures to match final implementation (they may have changed)
- Update design decisions if any were changed during implementation
- Remove TODO items that are now resolved

For `docs/index.md` (or equivalent):
- Add new module to the list with a one-line description

## Step 4: Verify

**If using frob:**
```bash
frob outline src/<module>/__init__.py
```

The outline should now show clean signatures. If a function looks confusing from
its outline alone, the docstring is insufficient -- revise it.

## Staleness check

After writing, verify every code example in docs actually works:

```bash
python -c "from <module> import <symbol>; help(<symbol>)"
```

**If any example is wrong, fix it before committing.** Stale docs are worse than no docs
because they actively mislead future readers (including yourself and agents).

## What NOT to document

- Private functions (leading underscore) -- only add if non-obvious invariant
- Trivial one-liners where name and types are self-documenting
- Implementation details obvious from reading the code
- The fact that you just wrote this ("Added in version X", "Used by Y")
