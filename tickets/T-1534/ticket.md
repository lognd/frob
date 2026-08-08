---
id: T-1534
title: WIRE001 false-positives on autouse pytest fixtures (no call-site to find)
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_wire.py
- tests/test_ticket_land.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'root-caused: T-1510 (landed after these two frob:waive WIRE001 follow_up=T-1534
    waivers were written) already added the autouse-pytest-fixture exemption to _new_callable_records
    via _is_autouse_pytest_fixture -- verified directly against the live graph snapshot
    that both _isolate_from_host_git_config and _pin_v1_mode_on_bare_tmp_path are
    now correctly recognized and excluded. The two waivers are dead weight; removing
    them is the actual fix this ticket asks for, not a scope-widening tangent'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'root-caused: T-1510 (landed after these two frob:waive WIRE001 follow_up=T-1534
    waivers were written) already added the autouse-pytest-fixture exemption to _new_callable_records
    via _is_autouse_pytest_fixture -- verified directly against the live graph snapshot
    that both _isolate_from_host_git_config and _pin_v1_mode_on_bare_tmp_path are
    now correctly recognized and excluded. The two waivers are dead weight; removing
    them is the actual fix this ticket asks for, not a scope-widening tangent'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit
- tests/unit/test_ticket_store.py::TestSlugify::test_lowercases_and_hyphenates
designated_repro_test: null
threat: null
component: null
---
land-repair for t-1321: WIRE001 flags _isolate_from_host_git_config in
tests/test_ticket_land.py (T-1393's autouse pytest fixture that isolates
every fixture repo in this module from the host machine's real git
config) as unreached outside its own tests -- WIRE001's text scan looks
for name(...)-shaped call occurrences, but an autouse=True pytest
fixture is invoked implicitly by pytest's own fixture-injection
machinery, never by a literal name() call anywhere in the file. This is
the same class of detector gap as T-1502/T-1527 (WIRE001's text-scan
missing a real-but-non-call-shaped wiring mechanism), specialized to
autouse fixtures. Teach WIRE001 to recognize @pytest.fixture(autouse=True)
-decorated functions as wired by construction, or otherwise special-case
the shape.