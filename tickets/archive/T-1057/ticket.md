---
id: T-1057
title: 'frob ticket land: resolve --worktree to an absolute path before building the
  worktree venv python path'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- src/frob/app/config.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: 'The ticket''s own acceptance criterion and plan name the actual fix as

    Path(worktree).resolve() "at argument-parse time" -- that point is

    src/frob/app/config.py''s generic CLI-args-to-AppConfig path-field

    conversion loop (`d[path_field] = Path(val)`, no resolve), fed from

    src/frob/__main__.py''s `--worktree` argparse registration

    (`_add_ticket_land_parser`). Neither file is under src/frob/tickets/_land.py.

    Tracing the actual bug confirms this: `frob.tickets._land.land()` already

    resolves both `root`/`worktree` internally at its own top (`root, worktree

    = root.resolve(), worktree.resolve()`), so a relative --worktree path is

    NOT what breaks land() itself. The break is one layer up, in

    src/frob/app/ticket_runner.py''s `_land()` CLI wrapper: it reads

    `cfg.ticket_worktree` (still relative, since config.py never resolved it)

    and passes that UNRESOLVED value into `_shared_check_spawn_fn(worktree,

    cfg.ticket_id)` BEFORE `land()` is ever called -- that closure spawns

    `_python_for_tree(root)` (`root / ".venv" / "bin" / "python"`, root=the

    unresolved relative worktree path) via `subprocess.run(..., cwd=root)`,

    which is exactly the `[Errno 2]` reproduction: the child''s argv[0]

    executable path is resolved relative to the CALLING process''s cwd, not

    the `cwd=` target, so a relative worktree path breaks the spawn while an

    absolute one does not.


    Widening scope to include src/frob/app/config.py (the argument-parse-time

    conversion the ticket''s own plan names) so the fix lands exactly where

    the ticket describes it, rather than working around the real cause by

    patching ticket_runner.py''s derived local instead.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/app.md
  reason: AFFECT001 doc-drift closure for AppConfig/from_external edits required to
    fix the config.py bug per this ticket's own plan
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse::test_relative_worktree_arg_resolves_to_absolute
- tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse::test_absolute_worktree_arg_unchanged
designated_repro_test: null
acceptance:
- text: given frob ticket land invoked with a RELATIVE --worktree path from the repo
    root, when land runs worktree-venv subprocesses, then the venv python resolves
    correctly and the land proceeds identically to the absolute-path invocation
  evidence:
  - tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse::test_relative_worktree_arg_resolves_to_absolute
  - tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse::test_absolute_worktree_arg_unchanged
threat: null
component: null
---
Observed 2026-07-27: 'uv run frob ticket land T-0861 --worktree .claude/worktrees/agent-...' failed with [Errno 2] No such file or directory: '.claude/worktrees/agent-.../.venv/bin/python' while the identical command with an absolute --worktree path succeeded. Something in the land pipeline joins the worktree arg verbatim with .venv/bin/python and executes it from a cwd other than the invocation cwd. Fix: Path(worktree).resolve() at argument-parse time; regression test covering a relative invocation.