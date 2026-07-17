---
name: plan
description: Turn a goal into a ticket tree via the planner agent. Replaces the old design-doc+TODO.md workflow -- every actionable item becomes a ticket, not a checklist bullet. Use when starting a non-trivial task.
---

# plan

Goal in, ticket tree out. Nothing is "planned" until it is a ticket in the
queue -- a design doc alone is not dispatchable and gets forgotten.

## Step 1: Orient without reading files

```bash
frob map src/
frob ticket list                   # what's already queued -- don't replan it
```

Read only README.md and existing docs/ at this step. Don't read source files.

## Step 2: Identify risks BEFORE decomposing

Answer these before dispatching the planner:

1. **Error propagation** -- how do failures flow? (Result type, exceptions, error codes?)
2. **Dependency direction** -- sketch A->B->C. Would this create a cycle?
3. **Data ownership** -- which module owns each data type crossing boundaries?
4. **Concurrency/ordering** -- any shared state or ordering dependencies?
5. **Performance** -- any hot paths needing special data structures?

If a risk changes the design, resolve it now. Architectural problems fixed
before ticket creation cost far less than after tickets (and their scope)
are locked in.

## Step 3: Dispatch the planner agent

Give the `planner` agent the goal plus the risk answers from Step 2. It
decomposes the goal into a ticket tree (`frob ticket new` calls with
`parent`/`blocked_by` edges and a `scope` per leaf) and never writes code.

Do not create tickets yourself in this skill -- decomposition quality is
the planner's job; this skill only orients it and checks the result.

## Step 4: Large features still get a design doc -- but no TODO.md

For genuinely large features, a `docs/<feature>.md` design doc is still
appropriate (public API, data models, error types, design decisions,
integration points -- same shape as before). The difference: every
actionable item in it becomes a ticket via the planner, not a `TODO.md`
bullet. The doc explains the shape; the queue tracks the work.

```markdown
# <Feature Name>

One sentence: what it does and why.

## Public API
## Data models
## Error types
## Design decisions
## Dependencies
## Integration points
```

Link the doc from the parent ticket's body so implementers land on it.

## Step 5: Verify the tree before moving on

```bash
frob ticket list --parent T-0040     # every leaf the planner claimed to create
frob ticket show T-00xx              # spot-check scope is narrow, not src/**
```

- [ ] Every leaf ticket has a scope narrower than "the whole goal"
- [ ] `blocked_by` reflects real dependencies, not just creation order
- [ ] No leaf duplicates an already-queued ticket
- [ ] Design doc (if any) is linked from the parent ticket

Nothing else to do here -- dispatch `next` (or hand the tree to the human)
to start working the queue.
