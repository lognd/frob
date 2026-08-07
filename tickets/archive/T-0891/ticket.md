---
id: T-0891
title: 'ticket evidence: direct-pytest verification leaks caller''s FROB_WORKTREE/FROB_AGENT
  lease env into the spawned test process'
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working T-0821: `frob ticket evidence`'s direct-pytest
verification fallback (`_run_pytest_directly` in
src/frob/app/ticket_runner.py) spawns `uv run pytest <node_ids> -q -o
addopts=` inheriting the calling shell's full environment. When the
caller is a dispatched worktree agent (FROB_AGENT=1, FROB_WORKTREE=<this
worktree>, both required by every other `frob ticket` invocation per
docs/guides/agent-playbook.md section 1/3), any test that itself performs
real git worktree operations against a throwaway tmp_path fixture repo
(e.g. tests/test_ticket_land.py's `TestLand`/`TestPlannedStateAutoAdvanceOnLand`
classes) gets refused by `frob.tickets._worktree_guard.enforce_worktree_lease`
with `WorktreeLeaseViolation`: the guard sees FROB_WORKTREE pointing at
the AGENT's own worktree and refuses to let the test mutate its own
unrelated tmp_path repo, since that path does not match the leased
worktree.

The same test passes cleanly under `frob check`'s own coverage/test gate
stage (which apparently manages/sanitizes the pytest subprocess
environment differently) and under a plain `uv run pytest <node_id>` with
no FROB_AGENT/FROB_WORKTREE exported -- only `frob ticket evidence`'s
direct-invocation path is affected.

Workaround used in T-0821: unset both vars for just the one `frob ticket
evidence` call. Real fix belongs in `_run_pytest_directly` (and any sibling
runner-based verification path with the same shape) in
src/frob/app/ticket_runner.py -- strip FROB_AGENT/FROB_WORKTREE (and any
other worktree-lease env) from the subprocess environment before spawning
the verification pytest run, so a ticket's own evidence-recording step
never leaks the recorder's own lease into the tests being verified.

## Drop reason
- 2026-07-26: exact duplicate of T-0884 (same body, same scope)