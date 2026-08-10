---
id: T-2005
title: BUG002 repro-check silently drops its own PYTHONPATH override, so it verifies
  against the wrong source
state: done
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
- src/frob/gitio.py
- tests/test_gitio.py
- tests/test_gates_mutation_evidence.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gitio.py
  reason: 'T-2005: the real fix lives in gitio.run_argv (it had no env param at all);
    _mutation_evidence.py only threads env= through. Both test files carry the fail-first
    regression evidence.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gitio.py
  reason: 'T-2005: the real fix lives in gitio.run_argv (it had no env param at all);
    _mutation_evidence.py only threads env= through. Both test files carry the fail-first
    regression evidence.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: 'T-2005: the real fix lives in gitio.run_argv (it had no env param at all);
    _mutation_evidence.py only threads env= through. Both test files carry the fail-first
    regression evidence.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/testing.md
  reason: 'T-2005: run_argv''s env parameter is documented there (public-api section),
    which now needs updating to reflect the fix'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gitio.py::TestRunArgv::test_env_override_reaches_the_spawned_process
- tests/test_gitio.py::TestRunArgv::test_env_none_inherits_the_calling_process_environment
- tests/test_gates_mutation_evidence.py::TestBugRepro::test_repro_run_actually_uses_the_parent_refs_own_pythonpath_override
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