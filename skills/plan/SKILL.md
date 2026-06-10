---
name: plan
description: Design and document a feature or module before any implementation. Use when the user says "plan X", "design X", "think through X", or when starting a non-trivial task. Writes design docs and TODO.md.
---

# plan

Design first, code never. This skill produces docs and TODO.md; nothing else.

## Step 1: Orient

```bash
frob map src/
```

Read the map fully. Do NOT read individual files yet.
Then read README.md (always) and any existing docs/ that are relevant.

## Step 2: Identify risks

Before writing anything, answer these questions:

1. **Error handling**: how do errors propagate? Use `typani.Result[T, E]` + `ErrorSet`.
   Every public function that can fail must return `Result`, never raise.
2. **Import cycles**: sketch the dependency graph. If A->B->A would happen, redesign now.
   Run `frob cycle src/ --suggest` after stubs exist.
3. **Data flow**: what are the types at each boundary? Define `BaseModel` for all data crossing module lines.
4. **Logging**: all user-visible output goes through `frob.logging.get_logger(name)`.
   No `print()`. No bare `logging.getLogger()`.
5. **Config**: if the feature has user-tunable options, add fields to `AppConfig` in `app/config.py`.

## Step 3: Write design doc

Write `docs/<feature>.md`:

```markdown
# <Feature Name>

One sentence: what it does and why.

## API

```python
def public_function(arg: Type) -> Result[ReturnType, FeatureError]:
    ...
```

## Data models

```python
class FeatureModel(BaseModel):
    field: type
```

## Errors

```python
class FeatureError(ErrorSet):
    ReasonOne = "human readable message"
    ReasonTwo = "human readable message"
```

## Design decisions

- Decision A: why, alternatives considered
- Decision B: why, alternatives considered

## Dependencies

- `frob.ast.python` -- for parsing Python files
- ... (list only direct imports)
```

## Step 4: Write TODO.md entries

Append to (or create) `TODO.md`. Use this format:

```markdown
## <Feature Name>

### Stubs
- [ ] src/frob/<feature>/__init__.py -- FeatureError, public_function stub
- [ ] src/frob/<feature>/_impl.py -- internal helpers

### Tests (unit)
- [ ] tests/test_<feature>.py -- happy path
- [ ] tests/test_<feature>.py -- error cases
- [ ] tests/test_<feature>.py -- edge cases

### Tests (integration)
- [ ] tests/test_integration_<feature>.py -- interaction with <other module>

### Tests (system)
- [ ] tests/test_system.py -- frob <cmd> end-to-end

### Implementation
- [ ] <function_name> -- one line description
- [ ] <function_name> -- one line description

### Documentation
- [ ] docs/<feature>.md -- update after implementation
- [ ] docstrings for all public functions
```

Every item in TODO.md must be independently dispatchable -- specific enough that
a Haiku agent can implement it from a bundle + the TODO line alone.
