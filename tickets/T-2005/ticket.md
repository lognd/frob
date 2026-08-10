---
id: T-2005
title: BUG002 repro-check silently drops its own PYTHONPATH override, so it verifies
  against the wrong source
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`_run_designated_test` (src/frob/gates/_mutation_evidence.py) builds a
`PYTHONPATH`-overridden `env` dict pointed at the parent-commit worktree's
own `src/`, but the `run_argv(argv, cwd=worktree, timeout_s=timeout_s)`
call two lines later never passes `env=env` through -- `run_argv` itself
has no `env` parameter at all. The spawned pytest subprocess therefore
inherits the CALLING process's environment unchanged, with no PYTHONPATH
override, so for a pure-Python source change it imports `frob` via the
current venv's editable-install `.pth` (which points at the WORKING
worktree's real `src/`, unaffected by `cwd`), not the parent commit's
checked-out source. `bug_repro_outcome_at_ref` / `frob ticket evidence
--check-repro` and the land/close-time BUG002 gate both silently check
the CURRENT (already-fixed) source against the parent ref, not the
parent's actual pre-fix source -- every "PASSED_AT_PARENT" verdict for a
pure-Python change is potentially a false positive.

Found while landing T-1987: `--check-repro` reported PASSED_AT_PARENT
(confirmatory-only) for a test that manually reproduces as FAILED when
the same env/cwd/argv shape is replicated by hand with PYTHONPATH
actually applied. Root cause confirmed by inspecting `run_argv`'s
signature (`src/frob/gitio.py::run_argv`) -- it accepts no `env` kwarg,
so `_run_designated_test`'s own `env` local is dead: built, then dropped.

Fix: either add an `env` parameter to `run_argv` (and thread it through
`guarded_subprocess_run`) and pass `env=env` from `_run_designated_test`,
or spawn the repro subprocess through a different primitive that does
accept `env`. Add a regression test that actually asserts the parent-ref
worktree's OWN source is what gets imported (not the calling venv's),
so a future refactor cannot silently reintroduce this.
