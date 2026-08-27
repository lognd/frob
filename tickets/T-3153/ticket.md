---
id: T-3153
title: Corpus test's own tmp_path ticket fixture trips the worktree-lease guard
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_refactor_corpus.py
- src/frob/tickets/_worktree_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description + plan

MEASURED while recording evidence for T-3143: `tests/test_refactor_corpus.py::TestRefactorCorpus::test_split_moves_symbols_across_every_call_site_shape` (T-3110/T-3119, pre-existing, unmodified by T-3143's own edits to this call) FAILS whenever it is run individually inside an agent's leased worktree (`FROB_WORKTREE`/`FROB_AGENT` set), which is exactly the context `frob ticket evidence`'s own "verify individually" re-check runs test ids in.

Root cause: the fixture's `new_ticket(root, ...)` call (line ~261, `root` = pytest's own `tmp_path`, a throwaway git repo OUTSIDE the leased worktree) hits `frob.tickets._worktree_guard`'s mutation refusal:

```
ERROR frob.tickets._worktree_guard: worktree-guard: agent leased to
<worktree>; refusing to mutate <tmp_path> (cwd resolved to <tmp_path>)
```

Reproduced identically against `main`'s own unmodified copy of this test file (confirmed via `git show main:tests/test_refactor_corpus.py`, same failure, same guard message) -- this is NOT something T-3143 introduced. It is orthogonal to T-3143's own fix and only surfaces because `frob ticket evidence`'s individual-rerun path is the first thing that happens to exercise this test id alone, inside an agent worktree lease, since the test was added (T-3110).

Effect: this test can never be bound as `frob:tests` evidence by an agent working inside a leased worktree (the standard dispatch shape), even though the test genuinely passes both standalone (outside any lease) and as part of a full suite run. It had to be left OUT of T-3143's own evidence citations for exactly this reason.

Fix direction (not investigated in depth): either (a) the corpus fixture's `new_ticket` call needs to run with the worktree-guard's env vars cleared/scoped to its own `tmp_path` (the same class of fix `_repo`/`_commit_all`'s own git calls already don't need, since they don't go through `frob.tickets`), or (b) `frob.tickets._worktree_guard` needs an exemption for a call whose target repo root is genuinely outside the agent's own repo entirely (a disposable pytest tmp_path repo, not a sibling worktree of the SAME repo the guard is protecting).

## Scope + leases
- tests/test_refactor_corpus.py
- src/frob/tickets/_worktree_guard.py
