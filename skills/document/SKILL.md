---
name: document
description: Write docstrings and update docs/ after implementation is complete. Use when the user says "document X", "add docs", "write docstrings", or as the final step in the develop pipeline.
---

# document

Add docstrings to public functions and update docs/ to match the implementation.
Documentation describes the WHAT and WHY, never the HOW (that is the code's job).

## Step 1: Identify what needs docs

```bash
frob map src/
```

Find all public functions (no leading underscore) that lack a docstring.
For each file, run:

```bash
frob outline src/frob/<module>/__init__.py
```

## Step 2: Write docstrings

Rules:
- One line only for simple functions. Multi-line only if behavior is non-obvious.
- Describe what the function does, not how.
- Include return type semantics: "Returns Ok(X) on success, Err(FeatureError.Y) if Z."
- Do NOT describe parameters that are self-evident from their name and type.
- No ASCII art, no elaborate headers, no parameter tables.

Format:
```python
def function_name(arg: Type) -> Result[X, E]:
    """Short description. Returns Ok(X) or Err(E.Reason) if condition."""
```

For complex functions:
```python
def complex_function(arg: Type) -> Result[X, E]:
    """
    Short summary line.

    Longer explanation only if the behavior has non-obvious constraints or
    invariants that would surprise a reader.
    """
```

## Step 3: Update docs/

For each feature doc (`docs/<feature>.md`):
- Update API signatures to match final implementation
- Add/update any design decisions that changed during implementation
- Update the "Dependencies" section if imports changed

For `docs/index.md`:
- Add the new module to the feature list with a one-line description

## Step 4: Update agentic-workflow.md if relevant

If the new feature is useful to future agentic sessions, add it to the
token budget table and the core loop in `docs/agentic-workflow.md`.

## Step 5: Verify

Read back the docstrings with `frob outline`:

```bash
frob outline src/frob/<module>/__init__.py
```

The outline should now show clean signatures. If a function looks confusing
from its outline alone, the docstring is not good enough -- revise it.

## What NOT to document

- Private functions (`_foo`) -- only if they contain a non-obvious invariant
- Trivial one-liners where the name and types are self-documenting
- Implementation details that are obvious from reading the code
- The fact that you just implemented this (it will rot)
