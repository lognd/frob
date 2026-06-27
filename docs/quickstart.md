# frob quickstart

A practical guide for a new user.

---

## Install

```bash
pip install frob
```

---

## Understand an unfamiliar codebase in 3 steps

```bash
# 1. Map: full symbol inventory (~200 tokens)
frob map src/

# 2. Pick a file, get its skeleton
frob outline src/frob/edit/__init__.py

# 3. Drill into a specific function (auto-sizes to the right depth)
frob ctx src/frob/edit/__init__.py replace
```

---

## Edit a function safely

### Single agent

```bash
# See what it looks like first
frob edit src/frob/edit/__init__.py replace

# Write replacement, apply immediately
echo "$new_source" | frob edit src/frob/edit/__init__.py replace --immediate
```

### Multiple agents on the same file (concurrent)

```bash
# Each agent stages independently -- no contention
echo "$new_replace" | frob edit src/frob/edit/__init__.py replace --stage
echo "$new_commit"  | frob edit src/frob/edit/__init__.py commit  --stage

# One commit step applies both atomically
frob edit src/frob/edit/__init__.py --commit
```

---

## Run the quality gate

```bash
frob check src/                  # Python: ruff+ty+cycle+dup+arch+bind+exports
frob check . --type cpp          # C++: cmake+clang-tidy+clang-format+ctest
frob check . --type rust         # Rust: cargo check+clippy+fmt+test
```

---

## Scaffold a new project

```bash
frob scaffold list
frob scaffold new python-library mylib
cd mylib
```

---

## Find where something is used

```bash
frob xref replace src/           # find every call to `replace`
```

---

## Check for problems before committing

```bash
frob cycle src/                  # import cycles
frob dup src/                    # duplicated blocks
frob arch src/                   # long functions, god classes
```

---

## See recent changes in conventional commit format

```bash
frob gitlog                      # user-visible changes
frob gitlog --level changelog    # release notes
```

---

## Track work across sessions

```bash
frob todo add "needs integration test for dispatch collect edge case"
# ... next session ...
frob todo list
frob todo done 1
```

---

## Dispatch parallel agents

```bash
# Create isolated worktrees
frob dispatch create "fix-auth"
frob dispatch create "add-tests"

# ... agents work independently, commit in their worktrees ...

# Collect completed work
frob dispatch collect <id1>
frob dispatch collect <id2>
```

---

## Parse tool output compactly

```bash
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
ruff check src/ | frob parse ruff
ty check src/ 2>&1 | frob parse ty
cargo clippy 2>&1 | frob parse cargo
```

---

## Next steps

- `docs/agentic-workflow.md` -- orchestrating parallel subagents
- `docs/edit.md` -- full staging model reference
- `docs/check.md` -- quality gate flags
- `docs/dispatch.md` -- branch-per-agent isolation
- `docs/mission.md` -- agent briefing system
