---
id: T-4085
title: ticket_runner.run() ambient-cwd resolution accepts a directory with no frob.toml
  and no git repo, silently writing the ledger there
state: done
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_ticket_runner_bare_root_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/unit/test_app_runners_batch7.py
  reason: T-4085's new tests moved into a dedicated file (test_ticket_runner_bare_root_guard.py)
    instead of the giant shared test_app_runners_batch7.py -- that file's hundreds
    of pre-existing cross-references would otherwise drag SCOPE002 findings for dozens
    of unrelated symbols into this narrow ticket's scope closure.
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_ticket_runner_bare_root_guard.py
  reason: T-4085's new tests moved into a dedicated file (test_ticket_runner_bare_root_guard.py)
    instead of the giant shared test_app_runners_batch7.py -- that file's hundreds
    of pre-existing cross-references would otherwise drag SCOPE002 findings for dozens
    of unrelated symbols into this narrow ticket's scope closure.
  actor: logan
  at: '2026-09-06'
evidence:
- tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard::test_ambient_cwd_with_no_frob_toml_or_git_is_refused
- tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard::test_ambient_cwd_inside_a_real_frob_repo_still_works
- tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard::test_explicit_path_to_a_bare_directory_is_still_trusted
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer Lab1-Reference (frob 0.530.0, 2026-09-06): frob ticket new run from a
directory that is NOT A REPO (a scratchpad under /tmp) resolved that directory
as the root and created a ticket ledger there instead of refusing. Sixty
tickets were created into the wrong place before it was noticed.

RELATED TO T-3983 BUT NOT A DUPLICATE. T-3983 is ticket-store writes resolving
from cwd when cwd sits inside a STALE WORKTREE OF A REAL FROB REPO -- write
lands in a valid-but-wrong ledger. This is one step further: cwd is not inside
any frob repo at all. Same root cause (cwd is the wrong authority for a store
write), narrower fix (a refusal, not a resolution policy). Filed separately;
scope (src/frob/app/ticket_runner/__init__.py) does not overlap T-3983's
(src/frob/tickets/_store.py) and neither blocks the other.

ROOT RESOLUTION TODAY (read _resolve_ticket_root and run() in
src/frob/app/ticket_runner/__init__.py): --path wins if given, else FROB_ROOT
env, else cwd. None of the three checks for frob.toml or .git; run()
dispatches straight into the handler once a Path resolves.

WHY A BLANKET GUARD IS WRONG (checked against the suite before proposing
this): 36 test files build AppConfig(ticket_path=tmp_path) and call
ticket_run against a bare tmp_path with neither frob.toml nor .git --
deliberate test isolation. An unconditional refuse-if-neither guard in run()
would break all of them. The actual incident's distinguishing fact: nothing
pinned the root deliberately -- no --path, no FROB_ROOT. An explicit --path or
FROB_ROOT is already a deliberate pin (matches "an explicit CLI flag always
wins", T-1674) and should keep being trusted outright.

THE FIX: in run(), when NEITHER --path nor FROB_ROOT was given (ambient-cwd
fallback), also require the resolved root to have a frob.toml OR .git before
dispatching; refuse otherwise (exit 1) naming the resolved directory and what
was missing. Does not touch the explicit-path/FROB_ROOT branches, so cannot
regress T-1674 or the 36 tmp_path tests.

BOOTSTRAP OUTSIDE A FROB REPO: frob scaffold new lives in a separate runner,
not this dispatch table, and is untouched. Within ticket_runner's table, no
verb (migrate included) legitimately needs neither frob.toml nor .git.

MUST-FIRE: frob ticket new, ambient cwd, no frob.toml/.git -- refused, message
names the resolved directory.
MUST-STAY-QUIET: ambient cwd inside a real frob repo still works.
THIRD FIXTURE: frob scaffold new (bootstrap) untouched, never reaches this
dispatch path.

ACCEPTANCE
- Guard in run(), applied ONLY to the ambient-cwd-fallback case.
- Refusal message names the resolved directory and what was missing.
- All three fixtures added to tests/unit/test_app_runners_batch7.py.
- Existing suite for this module still green.