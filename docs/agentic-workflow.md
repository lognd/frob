# Agentic Workflow Guide

How to use frob when acting as an orchestrator dispatching subagents.

---

## Core principle: minimize token cost, maximize parallelism

```
orient -> investigate -> dispatch -> collect -> verify
```

Every step has a frob tool designed for it. Don't read files directly until
you've exhausted cheaper options.

---

## Step 1: Orient

```bash
frob map src/                    # ~200 tokens: full symbol inventory
frob gitlog --level user -n 10   # ~100 tokens: recent user-visible changes
frob todo list                   # cross-session TODOs from prior sessions
```

`frob map` tells you which files are relevant. Read nothing else yet.

---

## Step 2: Investigate

For each relevant symbol, use `frob ctx` -- it auto-picks the right depth:

```bash
frob ctx src/frob/edit/__init__.py replace
# -> tier=bundle, reason=24 lines, 3 deps
# -> emits function + import signatures
```

Only reach past `frob ctx` when you need something specific:

| Need | Tool |
|------|------|
| Who calls this function? | `frob xref SYMBOL src/` |
| What's exported from this package? | `frob exports src/pkg/` |
| Are there cycles in the new dep graph? | `frob cycle src/` |
| Is this pattern already abstracted? | `frob dup src/` |
| What do the docstrings say? | `frob docs FILE --search QUERY` |
| Full file skeleton without bodies | `frob outline FILE` |

---

## Step 3: Quality baseline

Before dispatching, understand what's already broken:

```bash
frob check src/
```

This prevents agents from reporting pre-existing issues as their own errors.

---

## Step 4: Dispatch agents

### Small tasks (one function, one agent)

```bash
frob mission new fix \
  --file src/frob/edit/__init__.py \
  --target replace \
  --error "AttributeError: 'NoneType' object has no attribute 'splitlines'"
# -> .frob/missions/a1b2c3d4.md  (briefing with frob ctx embedded)
```

Give the mission ID to the sub-agent. It reads the briefing, does the work,
and calls `frob mission done a1b2c3d4` or `frob mission stuck a1b2c3d4 reason`.

### Parallel tasks editing different files

```bash
# Create isolated worktrees
frob dispatch create "fix-edit"
frob dispatch create "add-ctx-tests"
# Each agent commits in their worktree independently

# Collect after agents finish
frob dispatch collect <id1>
frob dispatch collect <id2>
```

### Parallel tasks editing the same file

Use the staging model instead of dispatch (lighter weight):

```bash
# Agent A stages foo, Agent B stages bar -- no contention
echo "$new_foo" | frob edit src/file.py foo --stage
echo "$new_bar" | frob edit src/file.py bar --stage   # concurrent, safe

# After both agents done:
frob edit src/file.py --commit      # atomic: re-parse, apply both, write once
```

---

## Step 5: Verify

```bash
frob check src/                       # aggregate gate
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
```

---

## Agent selection guide

| Task | Agent | Model |
|------|-------|-------|
| Implement one stubbed function | implementer | Haiku |
| Fix one failing test | debugger | Haiku |
| Write unit tests for one function | tester | Haiku |
| Write CLI end-to-end tests | system-tester | Sonnet |
| Write integration tests | integration-tester | Sonnet |
| Design a new module | architect | Sonnet |
| Review code for issues | reviewer | Sonnet |
| Safe structural refactor | refactorer | Sonnet |
| Quick yes/no architectural decision | oracle | Opus |
| Build base classes / protocols | smart-start | Sonnet |
| Decompose + coordinate large task | orchestrator | Sonnet |

---

## Token budget reference

| Operation | Typical tokens |
|-----------|--------------|
| `frob map src/` | 150-300 |
| `frob outline FILE` | 30-80 |
| `frob ctx FILE SYMBOL` (stub tier) | 20-80 |
| `frob ctx FILE SYMBOL` (bundle tier) | 200-600 |
| `frob ctx FILE SYMBOL` (full tier) | 400-1200 |
| `frob xref SYMBOL src/` | 50-150 |
| `frob gitlog --level user -n 10` | 50-150 |
| `frob parse pytest` (100-test run) | 10-20 |
| `frob parse ruff` | 5-30 |
| Reading a file directly | 300-5,000+ |

---

## Cross-session tracking

```bash
frob todo add "reviewer flagged god class in check/__init__.py"
frob todo add "need integration test for dispatch + mission"
frob todo list   # next session: pick up where you left off
```

---

## Full example: fix a failing test + add coverage

```bash
# 1. Orient
frob map src/frob/
frob gitlog --level user -n 5

# 2. Understand the failure
frob ctx src/frob/edit/__init__.py _apply_patch_to_content

# 3. Check baseline
frob check src/ --skip-ty

# 4. Brief the fix agent
frob mission new fix \
  --file src/frob/edit/__init__.py \
  --target _apply_patch_to_content \
  --error "EditError.ParseFailed returned for valid Python"
# [Haiku debugger agent handles it, calls mission done]

# 5. Brief the test agent
frob mission new test \
  --file src/frob/edit/__init__.py \
  --target _apply_patch_to_content
# [Haiku tester agent handles it, calls mission done]

# 6. Collect (they were both staging to the same file)
frob edit src/frob/edit/__init__.py --commit

# 7. Verify
frob check src/
pytest tests/unit/test_edit_staging.py --tb=short 2>&1 | frob parse pytest --exit-code $?
```

---

## BLOCKER handling

If a sub-agent returns a BLOCKER:

1. Read the blocker message carefully.
2. Check if multiple agents report the same structural problem.
3. If yes: dispatch a smart-start or architect agent to fix the root cause FIRST.
4. Reissue the original missions after the structural fix lands.

Never issue a workaround mission for a reported blocker. That creates tech debt that
compounds across agent generations.
