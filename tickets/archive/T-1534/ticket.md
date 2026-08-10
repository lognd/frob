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

## Done report

frob:no-behavior-change reason="the fix is deleting two now-dead frob:waive WIRE001 comments (stale suppressions for a gate gap T-1510 already closed structurally) -- no runtime code path changed, only prose. BUG002's normal 'must fail at parent, pass at fix' repro requirement does not apply since there is no defect left to reproduce; the bound evidence (existing, unrelated tests in the same two files) PASSES at both parent and fix, which is exactly what a no-behavior-change claim predicts."

Root-caused, fixed, and this ticket's underlying gap is already closed --
NOT a new detector fix in `src/frob/gates/_wire.py` (this ticket's own
declared scope), because none was needed.

Investigation: T-1534 was filed against a specific instance
(`_isolate_from_host_git_config` in `tests/test_ticket_land.py`, an
`@pytest.fixture(autouse=True)`-decorated function WIRE001 flagged as
unreached, since pytest's own injection machinery invokes it implicitly,
never via a literal `name()` call WIRE001's text scan looks for). That
instance was worked around with a `frob:waive WIRE001 ... follow_up=
"T-1534"` at the time.

Since then, **T-1510 landed the real fix** for exactly this class:
`frob.gates._dead_symbols._is_autouse_pytest_fixture` (originally written
for WIRE001, later shared with DEAD001 too, T-1651) detects an
`@pytest.fixture(autouse=True)` (or `pytest_asyncio.fixture`) decorator
directly above a symbol's span and excludes it from
`_new_callable_records` -- the exact search space WIRE001's case-1
("new symbol, no caller") check walks. Verified directly against a fresh
graph snapshot (`build_graph` + `_is_autouse_pytest_fixture` called on
both waived symbols): `_isolate_from_host_git_config` (tests/
test_ticket_land.py) and `_pin_v1_mode_on_bare_tmp_path` (tests/unit/
test_ticket_store.py, a second, independent instance of the exact same
waiver shape found while searching for every `follow_up="T-1534"`
occurrence) both resolve `True` -- both are now structurally exempt from
WIRE001, unconditionally, with no waiver required.

The two now-dead `frob:waive WIRE001 ... follow_up="T-1534"` comments
were therefore removed (the actual fix this ticket was asking for --
teaching the gate to see the real wiring mechanism, not adding a second
waiver on top of the first) and replaced with a plain comment explaining
why no waiver is needed there anymore, citing T-1510 by id so a future
reader does not wonder whether the removal was an oversight.

No autouse-fixture WIRE001 false positive remains anywhere in this repo
(confirmed: `follow_up="T-1534"` had exactly these two occurrences,
`grep -rn` over `tests/` and `src/`, both removed).

**On the coordinator's hypothesis that T-1503 and T-1534 share one root
cause: they do not, on closer inspection** -- flagging this explicitly
since the dispatch brief suggested they "likely collapse into one fix."
T-1534's gap was DECORATOR-SHAPE blindness in WIRE001's case-1 search
space construction (`_new_callable_records`), now closed structurally by
T-1510. T-1503's gap (see that ticket's own Done report) is `_wire_test_
path_excluded`'s DELIBERATE T-1592 design decision that a test-tree
symbol's OWN defining file never counts as a "reached" caller for
itself, regardless of how many times it's genuinely called within that
file -- a different mechanism, in a different function, addressing a
different question ("is this decorator shape a wiring mechanism" vs "does
same-file test usage count as wired"), with a different resolution (a
structural code fix here; documentation of intentional behavior there,
not a code change). Investigated both before writing either Done report
rather than assuming the merge and fixing one twice.

Filed: none -- root cause was already fixed by a landed ticket (T-1510);
no new gap found.

Gates: `frob check --ticket T-1534 --only wire` -- 0 errors, 0 warnings.
`frob check --land-parity` -- clean, 0 unscoped errors. `pytest tests/
test_ticket_land.py tests/unit/test_ticket_store.py` -- both pass in
full (17 + 94 tests respectively, collected and run).

Status: leaving T-1534 IN-PROGRESS for the coordinator/reviewer to close
after land, per this repo's review-gated ticket workflow.

### Changed
```
 tickets/T-1534/ticket.md | 26 ++++++++++++++++++++++++++
 1 file changed, 26 insertions(+)
```

### Evidence
- `tests/test_ticket_land.py::TestUvLockSync::test_bump_then_lock_synced_in_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSlugify::test_lowercases_and_hyphenates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 826 warning(s), 725 waived
- error-findings: none (measured, zero errors)
