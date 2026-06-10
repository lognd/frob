---
name: fix
description: Run all tools, parse output, and fix errors by dispatching Haiku debugger agents. Use when tests fail, linter errors exist, or type errors appear. Use when the user says "fix errors", "fix tests", "fix linting", or as part of the develop pipeline.
---

# fix

Run tools, parse compact output, fix one error at a time. Never fix blindly in bulk.

## Step 1: Run all tools and collect summaries

```bash
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $? > /tmp/tests.txt
ty check src/ 2>&1 | frob parse ty > /tmp/types.txt
ruff check src/ --output-format json | frob parse ruff > /tmp/lint.txt
```

Read all three files (~50 tokens total). Triage:

1. **Type errors first** -- they indicate wrong data flowing between modules
2. **Test failures second** -- they indicate wrong behavior
3. **Lint errors last** -- they are mechanical, fix in batch at the end

## Step 2: Fix type errors

For each type error, check the context:

```bash
frob xref <symbol> src/          # who passes this value?
frob stub src/frob/<file>.py <function_name>  # what does the function expect?
```

If the error is in a function body, dispatch a `debugger` agent:

```bash
frob bundle src/frob/<module>/__init__.py <function_name> > /tmp/ctx.md
```

```
You are fixing a type error. Context:

{contents of /tmp/ctx.md}

Error:
{exact line from /tmp/types.txt}

Fix ONLY the type error. Do not refactor. Do not change behavior.
Return ONLY a unified diff. No prose.
```

Apply, then re-run `frob parse ty` to confirm the error is gone.

## Step 3: Fix test failures

For each failing test:

1. Read the test to understand what it expects
2. Read the function being tested with `frob stub`
3. Decide: is the test wrong, or is the implementation wrong?

If implementation is wrong, dispatch `debugger` agent:

```bash
frob bundle src/frob/<module>/__init__.py <failing_function> > /tmp/ctx.md
```

```
You are fixing a failing test. Context:

{contents of /tmp/ctx.md}

Failing test:
{test name and failure message from /tmp/tests.txt}

Fix ONLY the implementation of `{function_name}`.
Do not change the test.
Return ONLY a unified diff. No prose.
```

After applying, run just that test file:

```bash
pytest tests/test_{module}.py::test_{name} --tb=short 2>&1 | frob parse pytest --exit-code $?
```

Confirm it passes before moving to the next failure.

## Step 4: Fix lint errors

Ruff errors are usually mechanical. Fix in batch yourself:

- `F401` unused import -- delete the import
- `E501` line too long -- break the line
- `F841` unused variable -- delete or use it
- `W291/W293` trailing whitespace -- auto-fixable

```bash
ruff check src/ --fix
ruff format src/
```

Then re-run `frob parse ruff` to confirm clean.

## Step 5: Final verification

```bash
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
ty check src/ 2>&1 | frob parse ty
ruff check src/ --output-format json | frob parse ruff
```

All must show zero errors before this skill is done.

## When to stop dispatching and fix manually

- The same function fails after 2 agent attempts: read the function fully and fix it yourself
- The error message is ambiguous: investigate with `frob xref` before dispatching
- The fix requires changes across multiple files: do it yourself, don't dispatch
- Import cycles appear: run `frob cycle src/ --suggest` and fix the structure

## Commit after clean

Once all tools pass, commit:

```bash
git add -p     # stage selectively
git commit -m "fix: <short description of what was broken>"
```
