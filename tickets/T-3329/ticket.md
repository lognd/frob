---
id: T-3329
title: frob ticket new has no project-root guard; confirm and scope a fix for F-019
state: queued
kind: bug
origin: human
created: '2026-08-28'
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
Split out of T-3303 (F-019 half). CONFIRMED: _resolve_ticket_root
(src/frob/app/ticket_runner/__init__.py) has NO "no project root found"
guard -- it resolves --path/FROB_ROOT/cwd and returns, unconditionally,
with no check that the resolved directory is a git repo or has a
frob.toml. F-024 (the reported diax friction, "frob ticket new run from
a scratch dir under /tmp with no git and no frob.toml wrote tickets/
there silently 49 times") reproduces exactly as described by reading
this function.

BUT: fixing this is NOT a drop-in guard. This repo's OWN test suite
(tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution.
test_no_frob_root_falls_back_to_cwd_default,
::test_resolved_root_is_logged_for_a_mutating_verb, and
TestTicketNewErrors) calls `_resolve_ticket_root`/dispatches
`frob ticket new` against a bare tmp_path with NO git repo and NO
frob.toml and asserts it SUCCEEDS. A guard that hard-refuses "not a
git repo / no frob.toml" as F-019 describes would break these
established, currently-passing tests -- meaning either (a) the tests
encode a deliberately-supported no-git/no-frob.toml mode this ticket
must not break, and the real fix is narrower (e.g. only refuse when
cwd drifted somewhere with pre-existing UNRELATED content, or only
warn), or (b) the tests themselves need to change as part of defining
what "a frob repo" means, which is a design call for a human/owner to
make, not something to default silently.

WHAT TO BUILD: decide and implement what "not a frob repo" means here
(git ancestor? frob.toml? tickets.md already present?), reconcile it
against TestTicketRunnerRootResolution/TestTicketNewErrors's existing
no-git contract (update or narrow those tests deliberately, with a
stated reason, if the decision requires it), then add the guard with a
clear error message before any write.

MUST-FIRE FIXTURE: `frob ticket new` from a cwd with no ancestor
frob.toml and no ancestor .git -- must exit non-zero with a clear
"not a frob repo" error and write nothing, WITHOUT breaking
TestTicketRunnerRootResolution's existing coverage (update those tests
deliberately if the decision requires bare-tmp_path support to no
longer be treated as valid).