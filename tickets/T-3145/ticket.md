---
id: T-3145
title: new_ticket-calling test fixtures spuriously fail evidence reverification under
  an agent's own FROB_WORKTREE lease
state: done
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
- tests/conftest.py
- tests/test_worktree_lease_env_ambient.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_worktree_lease_env_ambient.py
  reason: 'Ticket''s own fixture idiom needs a NEW pytest-collected test file to prove

    the ambient-FROB_WORKTREE-leak repro (conftest.py itself is not collected

    by pytest -- python_files = test_*.py -- so a test proving the fixture''s

    behavior cannot live only in conftest.py). T-3123, this ticket''s own

    sibling/precedent, declared BOTH its fixture file (tests/conftest.py) and

    a real test file (tests/test_ticket_land.py) in scope for exactly this

    reason. Adding tests/test_worktree_lease_env_ambient.py to scope,

    mirroring that precedent.

    '
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_new_ticket_against_unrelated_repo_is_unaffected_by_an_ambient_frob_worktree
- tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_opt_in_worktree_lease_guard_still_fires_when_deliberately_set
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27 while binding evidence for T-3108. enforce_worktree_lease
(T-0431) refuses new_ticket (and other lease-guarded ticket mutators) when
FROB_WORKTREE is set and does not match the write target's own resolved git
root. frob ticket evidence's individual-reverify path exports FROB_WORKTREE
into its pytest subprocess whenever the agent running the evidence check is
itself currently working inside a leased worktree -- which is the normal
case for a dispatched agent binding its own ticket's evidence.

Confirmed directly:
    FROB_WORKTREE=<a real leased worktree path> uv run python3 -c "
    from frob.tickets import new_ticket, TicketSpec, TicketKind, Origin
    from pathlib import Path
    new_ticket(Path('<some other tmp_path fake repo>'), spec)
    "
returns Err(WorktreeLeaseViolation), even though the target repo is a
completely unrelated tmp_path fixture, nothing to do with the leased
worktree at all.

This means ANY test that calls new_ticket (or any other enforce_worktree_
lease-guarded ticket mutator) against a tmp_path fake repo -- a common,
established fixture idiom in this repo (tests/test_gates.py's own TICK006
fixture family: test_tick006_refiles_and_rewrites_citation,
test_tick006_genuinely_lost_draft_still_caught_no_rename_no_duplicate, several
others) -- spuriously fails specifically when ITS OWN evidence binding is
reverified by an agent working under a real FROB_WORKTREE lease. Worked
around locally in T-3108's own new fixture module
(tests/test_gates_tick006_sibling_worktree.py) via
monkeypatch.delenv("FROB_WORKTREE", raising=False), but the EXISTING
tests/test_gates.py::TestFixEngineTierA TICK006 fixtures (already bound as
evidence for T-1544/T-2690/T-2702 and other landed tickets) do NOT have this
guard and are exposed to the same failure mode the next time an agent
reverifies their evidence from inside a leased worktree.

WHAT IS WANTED: either (a) an autouse fixture in tests/conftest.py that
clears FROB_WORKTREE for every test by default (tests/test_gates.py:10445
already shows the opt-in pattern for the one test that deliberately
exercises the guard -- that one would need to re-set it itself after an
autouse clear), matching this repo's own _neutralize_inherited_color_env/
_reset_parse_cache_before_test autouse precedent for exactly this "ambient
env leaks into a test subprocess" class, or (b) add the same
monkeypatch.delenv to every existing new_ticket-calling TICK006 fixture in
tests/test_gates.py individually. (a) is almost certainly the right shape:
one choke point, matching the two precedents already in conftest.py,
rather than repeating the same one-line fix at every call site indefinitely.

ACCEPTANCE
- A test that calls new_ticket (or any enforce_worktree_lease-guarded
  mutator) against a tmp_path fake repo must pass regardless of whether
  FROB_WORKTREE is set in the invoking process's environment. Must-fire
  fixture: set FROB_WORKTREE to an unrelated real path before running one
  of the existing TICK006 fixtures, confirm it currently fails, confirm the
  fix makes it pass.
- The opt-in test that deliberately exercises enforce_worktree_lease
  (tests/test_gates.py:10445 or wherever it lands) must still be able to
  set FROB_WORKTREE itself and see the guard fire -- the fix must not
  disable the guard, only stop it from leaking ambiently into tests that
  are not exercising it.