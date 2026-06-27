---
name: review
description: Review code quality, correctness, and design after implementation. Use when the user says "review X", "check X", or before committing. Checks error handling, test coverage, and design issues.
---

# review

Quality check before commit. Verify tools pass, then check design correctness.
Prioritize correctness over style.

## Step 1: Orient (do not read files yet)

**If using frob:**
```bash
frob map src/
frob cycle src/
```

**Otherwise:**
```bash
find src -name "*.py" | head -30
python -c "import <each_module>" 2>&1   # quick import cycle check
```

No cycles = prerequisite for everything else.

## Step 2: Run all verification tools

```bash
# Python
pytest tests/ -q 2>&1 | frob parse pytest --exit-code $?   # with frob
pytest tests/ -q                                            # without frob
ty check src/ 2>&1 | head -20
ruff check src/ --output-format json | head

# C++
cd build && ctest --output-on-failure
# compile with -Wall -Wextra and check for warnings
```

**All must pass before reviewing code.** Tools are faster and more reliable than manual review.

## Step 3: Error handling audit (most important)

For every public function that can fail:
- [ ] Returns a failure type (Result, error code, exception -- whatever the project convention is)
- [ ] Every failure case is actually reachable (no dead `Err` variants)
- [ ] Callers handle the failure (not silently ignored)
- [ ] No silent swallowing of errors (no bare `except: pass`, no unchecked `danger_ok`)

**If using typani specifically:**
- [ ] `.danger_ok` / `.danger_err` only used when `.is_ok` / `.is_err` was checked first
  (or use `.ok` / `.err` safe accessors that return None instead of crashing)
- [ ] All Result/Option accessors without `()` -- they are properties, not methods
- [ ] Chaining with `|` (map) or `>>` (and_then) where it clarifies flow
- [ ] ErrorSet variants have descriptive string values, not empty strings
- [ ] Merged error sets use `A | B` syntax (not manual re-declaration)

## Step 4: Test coverage audit

For each public function, check:
- [ ] Happy path test
- [ ] Each failure variant tested (failure is returned, not raised, if applicable)
- [ ] Edge case (empty, None, boundary)
- [ ] System/CLI test if it has a command-line entry point

Run `frob arch src/` (if available) or check manually:
- Any function >30 lines? Consider splitting
- Any class with >12 methods? Consider splitting
- Any file importing >8 other project files? Check for coupling

## Step 5: Staleness check (prevent stale references)

Before approving, verify every specific claim:

**Verify file paths exist:**
```bash
ls src/<module>/__init__.py  # referenced in docs or tests
```

**Verify function names:**
```bash
grep -n "def <function_name>" src/**/*.py  # referenced in tests/docs
```

**Verify import paths:**
```bash
python -c "from <module> import <symbol>"  # referenced imports
```

A stale reference (file moved, function renamed, wrong module path) is a hard block.

## Step 6: Logging and output audit (Python)

- [ ] No `print()` calls in `src/` -- use `get_logger(__name__)`
- [ ] Debug info at `DEBUG`, user output at `INFO`, warnings at `WARNING`, errors at `ERROR`
- [ ] No log messages inside tight loops (performance)

## Step 7: Documentation check

- [ ] Every public function has a docstring (one line is fine)
- [ ] No docstring describes implementation details ("iterates over the list")
- [ ] Docstrings mention non-obvious constraints, error conditions, or invariants

## Verdict

**Approve** (ready to commit) if:
- All tools pass
- No cycles
- Error handling complete
- No stale references
- Tests cover all error variants

**Block** if any above fail. List each specific issue with file:line.

## Commit

```bash
git add -p                       # stage selectively, review each hunk
git diff --staged                # final check
git status                       # confirm no unintended files
git commit -m "<type>: <short description>"
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
