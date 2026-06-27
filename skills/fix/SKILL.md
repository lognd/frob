---
name: fix
description: Run all tools, parse output, and fix errors one at a time. Use when tests fail, linter errors exist, or type errors appear. Emphasizes a tight single-test verification loop for maximum speed.
---

# fix

Run tools, parse compact output, fix one error at a time.
NEVER fix blindly in bulk. ALWAYS verify each fix with the single failing test before moving on.

## The fast fix loop (critical)

The most common mistake: fixing a bug, then running the full test suite to check.
Full suites are slow. The fast loop is:

```
1. Identify the ONE failing test
2. Run ONLY that test
3. Fix
4. Run ONLY that test again -> must pass
5. Run full suite -> confirm no regressions
```

```bash
# Step 1: find failing tests quickly
pytest tests/ --testmon -q 2>&1 | head -20
# or if no testmon:
pytest tests/ -x -q 2>&1 | head -20

# Step 2+3+4: single-test loop (fast)
pytest tests/test_module.py::TestClass::test_name -x --tb=short

# Step 5: full suite only after single test passes
pytest tests/ -q
```

**If using frob for compact output:**
```bash
pytest tests/ --testmon -q 2>&1 | frob parse pytest --exit-code $?
# Fix...
pytest tests/test_module.py::TestClass::test_name --tb=short 2>&1 | frob parse pytest --exit-code $?
```

## Step 1: Triage all failures

```bash
# Run all tools, get compact summaries
pytest tests/ -q 2>&1 > /tmp/tests.txt          # or with --testmon
ty check src/ 2>&1 > /tmp/types.txt             # if Python
ruff check src/ --output-format json > /tmp/lint.txt  # if Python
```

**Or with frob:**
```bash
pytest tests/ -q 2>&1 | frob parse pytest --exit-code $? > /tmp/tests.txt
ty check src/ 2>&1 | frob parse ty > /tmp/types.txt
ruff check src/ --output-format json | frob parse ruff > /tmp/lint.txt
```

Read all three (~50 tokens total with frob, or ~200 tokens without).

**Triage order:**
1. Type errors first -- indicate wrong data at module boundaries
2. Test failures second -- indicate wrong behavior
3. Lint errors last -- mechanical, fix in batch

## Step 2: Fix type errors

For each type error, understand the flow before touching anything:

```bash
# Where is the mismatched value coming from?
frob xref <symbol> src/          # if using frob
grep -rn "<symbol>" src/         # otherwise
```

Dispatch debugger agent or fix directly.
After fix: run ONLY the tests touching that module:
```bash
pytest tests/test_<module>.py -x --tb=short
```

## Step 3: Fix test failures -- single-test loop

For each failing test:
1. Identify whether test is wrong or implementation is wrong
2. If implementation wrong:
   - Get context: `frob bundle <file> <function>` or read the specific function
   - Fix
   - Run ONLY that test: `pytest tests/test_X.py::test_name -x --tb=short`
   - Must pass before moving to next failure
3. If test is wrong:
   - Verify the intended behavior from the design doc or function signature
   - Fix the test
   - Run it again

**When dispatching a debugger agent:**
```
Context: {frob bundle output or function body}

Failing test: {exact test name}
Error: {exact error message from --tb=short}

Fix ONLY the implementation of {function_name}.
Do not change the test. Minimal change only.

Single-function fix: output ONLY the new function source (no diff markers).
Multi-file fix: output a unified diff starting with `--- a/`.
```

After the agent responds:
```bash
# Single-function (output does not start with "--- a/"):
echo "$fix_output" | frob edit src/<module>/<file>.py <function_name> --immediate

# Multi-file (output starts with "--- a/"):
echo "$fix_output" | git apply

pytest tests/test_X.py::test_name -x --tb=short   # verify single test
```

**If the agent returned BLOCKER:**
- Bypass permissions OFF: surface BLOCKER + SUGGESTION to user verbatim, wait for decision.
- Bypass permissions ON: dispatch /oracle with the BLOCKER as the question, apply the DECISION,
  resume. Log "BLOCKER resolved via oracle: {DECISION}" for later review.
Patching over a structural problem hides it and guarantees it recurs. Never do it.

## Step 4: Fix lint errors (batch)

Mechanical fixes -- do these yourself, don't dispatch:
```bash
ruff check src/ --fix                 # auto-fix safe issues
ruff format src/                      # formatting
```

Manual: `F401` unused import (delete it), `E501` too long (break the line).

## Step 5: Final verification

```bash
pytest tests/ -q                              # all tests
ty check src/ 2>&1 | head -20               # type check
ruff check src/ --output-format json | head  # lint
```

All must be clean.

## When to stop dispatching and fix manually

- Same function fails after 2 agent attempts: read it fully and fix yourself
- Error requires cross-file changes: do it yourself
- Import cycles appear: `frob cycle src/ --suggest` or inspect imports manually, fix structure first
- The agent's diff touches more than the one failing function: reject it, fix manually
- Agent returned BLOCKER: do not fix manually either -- surface to user, resolve design first

## Commit pattern

```bash
git add -p          # stage selectively, review each hunk
git diff --staged   # confirm what you're committing
git commit -m "fix: <short description of what was broken and why>"
```
