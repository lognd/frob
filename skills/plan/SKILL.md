---
name: plan
description: Design and document a feature or module before any implementation. Use when starting a non-trivial task. Writes design docs and TODO.md. Works for any language or project type.
---

# plan

Design first, code never. This skill produces docs and a TODO checklist; nothing else.

## Step 1: Orient without reading files

**If using frob:**
```bash
frob map src/
```

**Otherwise:**
```bash
find src -type f | grep -E '\.(py|cpp|h|rs|go|ts)$' | sort
grep -r "^class \|^def \|^func \|^fn \|^pub " src --include="*.py" -l
```

Read only README.md and existing docs/ at this step. Don't read source files.

## Step 2: Identify risks BEFORE designing

Answer these before writing anything:

1. **Error propagation**: how do failures flow? (Result type? exceptions? error codes?)
2. **Dependency direction**: sketch A->B->C. Would adding your module create a cycle?
3. **Data ownership**: which module owns each data type? Does anything cross module boundaries?
4. **Concurrency/ordering**: any shared state, ordering dependencies, or async concerns?
5. **Performance**: any hot paths that require special data structures?

If you find a risk that changes the design, resolve it NOW before documenting.
Architectural problems fixed at design time cost ~10x less than after implementation.

## Step 3: Write design doc (docs/<feature>.md)

```markdown
# <Feature Name>

One sentence: what it does and why.

## Public API

List every public function/method with full typed signature and one-line description.

## Data models

Every structured data type (class, struct, record) crossing module lines.

## Error types

All failure cases and when they occur.

## Design decisions

For each non-obvious decision: what was chosen, alternatives considered, why.

## Dependencies

Direct dependencies only. For each: what it provides to this module.

## Integration points

Which existing modules call this. Which this calls. Any protocol contracts.
```

## Step 4: Write TODO.md entries

Append to (or create) `TODO.md`. Format every item to be independently dispatchable:

```markdown
## <Feature Name>

### Stubs
- [ ] src/<module>/__init__.py -- data models, error types, function signatures
- [ ] tests/test_<module>.py -- test file (empty, just imports)

### Tests
- [ ] tests/test_<module>.py::TestFunctionName -- happy path, error cases, edge cases
- [ ] tests/test_integration.py::test_<module>_with_<other> -- integration

### Implementation
- [ ] <function_name>(arg: Type) -> ReturnType -- one-line description
- [ ] <function_name>(arg: Type) -> ReturnType -- one-line description

### Documentation
- [ ] docs/<feature>.md -- update signatures after implementation
- [ ] docstrings for all public symbols
```

Every implementation TODO item must be specific enough that an agent can implement
it from a `frob bundle` output + the TODO line alone, with no additional context.

## Correctness check before signing off

- [ ] Every function that can fail has an explicit error type
- [ ] No circular dependencies in the design
- [ ] Every public function has a typed signature
- [ ] Design doc is specific enough to detect disagreements (not "returns result")
- [ ] TODO items are independently executable (no item depends on another's status being unknown)
