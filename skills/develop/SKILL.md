---
name: develop
description: Master orchestrator for building a new feature, module, or project from scratch. Use when the user says "build X", "implement X", "add X", or starts a new development task. Runs the full plan->test->implement->fix->document pipeline.
---

# develop

Full development pipeline. Runs plan, write-tests, implement, fix, document in order.
Dispatch subagents for individual functions; use this skill to orchestrate the whole task.

## Before anything else

```bash
frob map src/
```

This is ~200 tokens. Read it fully. Identify all relevant files before touching anything.
If the project has >20 files, check token cost before reading any file:

```bash
frob tokens src/some/file.py
```

Only read files with >200 tokens if you have no other choice. Prefer `frob outline` first.

## Step 1: Plan

Run `/plan` (or follow it inline):
- Read README.md and existing docs/ if present
- Identify architectural risks (error handling, cycles, protocol mismatches) and resolve them first
- Write/update `docs/<feature>.md` with design decisions
- Write/update `TODO.md` with a flat checklist of every function/class/test to write

Design doc must include:
- Module layout (what files, what goes in each)
- Public API signatures (typed)
- Error types (`ErrorSet` subclass)
- Data models (Pydantic `BaseModel`)
- Any cross-cutting concerns (logging, config, cycles)

## Step 2: Stubs

For each module to be created:
1. Write the file with all class/function definitions but `...` bodies
2. Include all imports, type annotations, and docstrings (one line max per function)
3. Verify no import cycles: `frob cycle src/ --suggest`

Stubs serve as the contract that tests and implementation agents both see.

## Step 3: Write tests

Run `/write-tests` (or follow it inline) before writing any implementation.
Unit tests first, then integration, then system (subprocess).

## Step 4: Implement

Run `/implement` (or follow it inline):
- Dispatch one Haiku agent per function/method via `frob bundle`
- Apply each diff, run `frob parse` on failures, fix or re-dispatch

## Step 5: Fix

Run `/fix` on any remaining test/lint/type failures.

## Step 6: Document

Run `/document` to add docstrings and update docs/.

## Checkpoints (stop and verify before continuing)

- After stubs: `frob cycle src/` must be clean
- After each agent diff applied: `frob parse pytest` must not increase failure count
- After implement: `frob parse pytest`, `frob parse ty`, `frob parse ruff` all clean
- Before document: all tests pass

## Token discipline

Never read a file raw if you can avoid it. The hierarchy:

| Token cost | Action |
|-----------|--------|
| ~10 | `frob tokens <file>` -- decide how to read |
| ~50 | `frob outline <file>` -- structure only |
| ~200 | `frob stub <file> <target>` -- area around one function |
| ~500 | `frob bundle <file> <target>` -- ready-to-dispatch context |
| 300-5000+ | `Read file` -- last resort for small files only |
