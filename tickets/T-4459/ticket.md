---
id: T-4459
title: Worktree test runs import frob from the ROOT src (editable .pth), measuring
  main instead of the branch
state: queued
kind: bug
origin: agent
created: '2026-09-13'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/agent_runner.py
- src/frob/app/ticket_runner/_work*.py
- src/frob/doctor.py
- tests/test_worktree_pythonpath*.py
- docs/modules/agent*.md
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
MEASURED 2026-09-13 by the T-4449 rebase agent: running the root checkout's interpreter (`/home/logan/projects/frob/.venv/bin/python -m pytest ...`) with a worktree as cwd imports `frob` from the ROOT src/ because the editable install's .pth points at /home/logan/projects/frob/src, not at the worktree's src/. A worktree test run therefore exercises main's code, not the branch under test, unless PYTHONPATH="$(pwd)/src" is set. The alternative agents use, `uv run` inside the worktree, builds a stray per-worktree .venv (seen today: a Python 3.11 venv in t-4445 whose `frob ticket body` sat in D-state for 50+ minutes). Both shapes silently mis-measure. ACCEPTANCE: (1) `frob ticket work`/`frob agent env` (whatever provisions or enters a worktree) exports PYTHONPATH=<worktree>/src (or installs the worktree's src editable into a shared venv) so the checked-out branch is what imports; (2) `frob doctor` in a worktree reports which src/ `import frob` resolves to and fails loudly when it is another checkout's; (3) a test that creates a worktree, runs python -c "import frob; print(frob.__file__)" through the documented entry point, and asserts the worktree path; (4) docs/modules (agent/worktree docs) state the rule. Sprint v0.532.0.
