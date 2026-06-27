---
name: develop
description: Master orchestrator for building a new feature, module, or project from scratch. Use when the user says "build X", "implement X", "add X", or starts a new development task. Runs the full plan->test->implement->fix->document pipeline.
---

# develop

Full development pipeline. Runs plan, write-tests, implement, fix, document in order.
Dispatch subagents for individual functions; use this skill to orchestrate the whole task.

## Before anything else: orient cheaply

**If the project uses frob:**
```bash
frob map src/
frob tokens src/some/file.py   # before reading any file
```

**Otherwise:**
```bash
find src -name "*.py" | head -30    # get file list
grep -r "def \|class " src --include="*.py" -l | head -20   # find key files
wc -l src/**/*.py | sort -rn | head -10   # find large files
```

Never read a file just to understand the project. Get structure first, then read only what's needed.

## Step 1: Plan

Run `/plan` (or follow it inline):
- Read existing docs (README, docs/) first
- Identify architectural risks before writing any code:
  - Error propagation: how do failures flow through the system?
  - Dependency direction: which module depends on which? Any cycles?
  - Data ownership: which module owns which data types?
- Write/update design doc in docs/ with API, data models, error types
- Write/update TODO.md with specific, independently-dispatchable tasks

## Step 2: Stubs

For each module to be created:
1. Write all class/function signatures with types, `...` bodies
2. Include all imports and one-line docstrings on public symbols
3. Check for cycles: `frob cycle src/` or `python -c "import <module>"` on each file

Stubs are the contract: tests and implementations both depend on them.

## Step 3: Tests (BEFORE implementing)

Run `/write-tests`.
Tests will fail at this stage -- that is correct and expected.
What must NOT happen: import errors, syntax errors, collection errors.

## Step 4: Implement

Run `/implement`.
One function at a time. Verify each before moving to the next.

## Step 5: Fix

Run `/fix` on any remaining failures.

## Step 6: Document

Run `/document`.

## Checkpoints

- After stubs: no import cycles
- After each implementation: failing test count must not INCREASE (new failures = regression)
- After all implementation: all tests pass
- Before commit: `frob arch src/` or equivalent manual check for new architectural debt

## BLOCKER handling (critical)

Any subagent (implementer, debugger, tester) may return:
```
BLOCKER: <design problem>
SUGGESTION: <what should change first>
```

**Default (bypass permissions OFF):**
1. STOP the current pipeline step immediately.
2. Do NOT re-dispatch the agent.
3. Do NOT apply a local workaround.
4. Surface the BLOCKER and SUGGESTION to the user verbatim and wait for a decision.

**Autonomous mode (bypass permissions ON):**
1. STOP the current pipeline step immediately.
2. Dispatch /oracle with the BLOCKER as the question and the SUGGESTION as context.
3. Apply oracle's DECISION, update stubs/design accordingly.
4. Resume the pipeline from the step that was blocked.
5. Log: "BLOCKER resolved via oracle: {DECISION}" so the user can review it later.

A BLOCKER is not a failure -- it is the agent doing its job correctly.
Never silently patch around one.

## Token discipline (if using frob)

| Cost | Action |
|------|--------|
| ~10 tok | `frob tokens <file>` -- decide reading strategy |
| ~50 tok | `frob outline <file>` -- structure only |
| ~200 tok | `frob stub <file> <target>` -- one function context |
| ~500 tok | `frob bundle <file> <target>` -- subagent dispatch context |
| 300-5000+ | Read file directly -- only for small/critical files |
