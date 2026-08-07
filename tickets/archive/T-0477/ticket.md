---
id: T-0477
title: 'recover/finish ''frob docs'' command: WIP preserved on branch worktree-agent-a08bb1e798ea69fa1
  (commit 4961fbe) -- src/frob/docs/ + app/docs_runner.py + __main__/app/config wiring,
  abandoned uncommitted in an orphaned WSL-path worktree; evaluate and either land
  or drop'
state: dropped
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
dropped 2026-07-21: commit 4961fbe does not exist anywhere in this repo's
object store (not on the named branch, not dangling, not in any reflog --
`git fsck --dangling --no-reflog` and a full reflog grep for the prefix
both come up empty). The named branch worktree-agent-a08bb1e798ea69fa1's
tip (7b88b77) is already a merged ancestor of main (`git merge-base main
worktree-agent-a08bb1e798ea69fa1` == the branch tip, `git diff
main...worktree-agent-a08bb1e798ea69fa1 --stat` is empty) and its content
is unrelated CI-template work, not docs/. Separately, and dispositively:
`frob docs` already exists on main today as a complete, tested, documented
command (`src/frob/app/docs_runner.py`, `src/frob/docs/__init__.py`,
`docs/modules/app.md` describing `docs_runner.run` and
`find_docs_dir`/`overview`/`search`), landed no later than commit
`3c71a1b` ("feat: add frob docs, frob bind, pybind11/pyo3 templates,
sync-skills, test reorganization") and carried forward through
`d8ca467`/`c4eeb5b`/`428c753`. There is nothing left to recover or land --
the WIP this ticket describes is either lost or already superseded by
what shipped. No evidence required for a dropped ticket per playbook
precedent (T-0475).