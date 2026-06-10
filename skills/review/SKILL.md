---
name: review
description: Review code quality, correctness, and design after implementation. Use when the user says "review X", "check X", "audit X", or before a commit. Checks for design issues, error handling gaps, and test coverage.
---

# review

Quality check after implementation. Run after all tests pass, before committing.

## Step 1: Orient cheaply

```bash
frob map src/
frob cycle src/
```

Confirm no cycles. Read the map to identify the scope of changes.

## Step 2: Check each changed file

For each modified file, run outline first:

```bash
frob outline src/frob/<module>/__init__.py
```

Then read the full file only if the outline reveals something to investigate.
For large files (>400 tokens), use `frob stub <file> <function>` to zoom in.

## Step 3: Error handling audit

For every public function:
- [ ] Returns `Result[T, E]`, not bare value or raised exception
- [ ] Every `ErrorSet` variant is actually reachable
- [ ] Callers handle the Err case (check with `frob xref`)
- [ ] No silent swallowing of errors (no bare `except:` or `result.danger_ok` without check)

## Step 4: Data model audit

For every `BaseModel`:
- [ ] All fields have correct types (no `Any` unless unavoidable)
- [ ] Required vs optional fields match actual usage
- [ ] `as_text()` and `as_json()` exist for any model that crosses a module boundary

## Step 5: Test coverage audit

```bash
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
```

For each public function, verify at minimum:
- [ ] Happy path test
- [ ] Each `ErrorSet` variant tested (Err returned, not raised)
- [ ] Edge case (empty, boundary)
- [ ] System test if it has a CLI entry point

Missing tests are a blocking issue -- add them before approving.

## Step 6: Logging audit

- [ ] All user-visible output uses `get_logger(name)`
- [ ] No `print()` calls anywhere in `src/`
- [ ] Debug info at `DEBUG` level, user output at `INFO`, warnings at `WARNING`, errors at `ERROR`

## Step 7: Dependency hygiene

```bash
frob cycle src/
```

Must be clean. If cycles exist, they are a blocking issue.

Also check `pyproject.toml`: every import that is not stdlib must be listed as a dependency.

## Verdict

**Approve** if:
- All tools pass (pytest, ty, ruff)
- No cycles
- Error handling is complete
- Tests cover all error variants
- No print() calls

**Block** if any of the above fail. Note each specific issue as a TODO item.

## After approval

```bash
git add -p
git status
git commit -m "<type>: <short description>"
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
