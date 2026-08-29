---
id: T-3305
title: _python_for_tree trusts a tree venv without checking frob is importable, breaking
  self-verification in every consumer repo
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: priority
  old_value: high
  new_value: critical
  reason: 'verified in code: _python_for_tree tests only is_file() on <root>/.venv/bin/python
    and never that frob is importable through it, so close/land gate-claim re-verification
    is a SILENT no-op in every consumer repo -- frob''s central enforcement promise
    does not work for anyone but frob''s own checkout, and a PyPI release ships that'
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-014). Root cause was
diagnosed by the REPORTER and independently CONFIRMED IN CODE here, precisely.

NOT covered by T-3275/T-3276 (those fix `_coverage_refresh.py`'s hardcoded
"src/frob" target and general external-tool resolution via `doctor.py` --
different files, different bug). This ticket is specifically
`_python_for_tree` in src/frob/app/ticket_runner/_verify.py.

CONFIRMED, src/frob/app/ticket_runner/_verify.py:737-772:

    def _python_for_tree(root: Path) -> str:
        venv_python = root / ".venv" / "bin" / "python"
        if venv_python.is_file():
            return str(venv_python)
        return sys.executable

This checks only that `<root>/.venv/bin/python` EXISTS as a file -- never
that it has `frob` importable. In a consumer repo, `.venv` is the PROJECT's
own venv (created by `uv sync`, populated with the project's own deps). frob
itself is installed as a global uv tool (`uv tool install frob`), never as a
project dependency, so that venv's python has no `frob` module at all.
`python -m frob check ...` through it exits 1 with "No module named frob".

DOWNSTREAM IMPACT: every done-report/close/land self-verification spawn
through this path reports "unmeasured" gates, so `close` refuses with
OwnObligationsUnclean while `frob check --delta --ticket` run directly from
the shell is clean -- the gate-claim re-verification machinery (T-1384/
T-1399) never actually gates anything in a consumer repo. Ironically a
worktree WITHOUT a venv works today (falls back to sys.executable) -- which
is exactly the state F-017 (a separate filed friction: `frob ticket work`
worktrees lack a venv) pushes users AWAY from.

WHAT NOT TO DO: do not just special-case "if this is frob's own repo" --
that fixes frob's own dogfooding but leaves every consumer repo broken,
which is the actual reported failure. Do not remove the tree-venv
preference either -- T-0846's reasoning for preferring it (checking the
TREE's own installed code, not the caller's) is sound and still needed for
frob's own repo and for any consumer repo that DOES install frob as a
project dependency.

WHAT TO BUILD: before trusting `<root>/.venv/bin/python`, verify `frob` is
actually importable through it (e.g. `<venv>/bin/python -c "import frob"`
exit 0), falling back to `sys.executable` when it is not -- exactly the
reporter's own suggested fix, and exactly the workaround they had to hand-
build per worktree via a `.pth` file bridging into the uv-tool venv's
site-packages (a real, working, but painfully manual fix that this ticket
should make unnecessary).

MUST-FIRE FIXTURE: a tree with a `.venv/bin/python` that does NOT have frob
installed (the normal state for any consumer repo using the global uv-tool
install) -- `_python_for_tree` must return `sys.executable`, and a
done-report/close spawn through it must produce a real, parsable gate
verdict, not "unmeasured".

MUST-STAY-QUIET FIXTURE: frob's own repo, whose `.venv` DOES have frob
importable (editable install) -- must keep preferring the tree venv exactly
as today (T-0846's DOC005 cross-check scenario must still work).
