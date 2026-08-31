## Done report

Measured all six named WARN families 2026-08-30 via targeted `uv run
frob check --only <gate> --json`, filtering severity=warning (the real
un-waived count -- the ticket's own 120 total mixed in some already-
waived findings from a coarser measurement):

  DEAD001: 23 (was reported 31)
  INV003: 12
  INV004: 12
  WALK001: 7 (was reported 36 -- 29 of those already carried live
    frob:waive directives and were already at severity=note)
  NEGEXIST001: 18
  LANG003: 27

Did the per-finding review T-2368's own body called for on the most
tractable family, WALK001 (7 real findings, 5 files): read
docs/modules/gates.md's WALK001 section, then reviewed each site's
actual root/pattern binding. All 7 are genuinely bounded, small-scope
walks -- a docs/ subtree glob (x4, _prose.py/_docstatus.py), a single
src/frob/<pkg> subpackage rglob (x2, _gate_cache.py/_support.py), and a
synthetic never-existing probe path (_models.py) -- never able to reach
.git/.venv/node_modules/build output, which is exactly the escape hatch
WALK001's own doc names ("Waivable per-line for a genuinely small,
bounded-scope walk"). Added a reasoned `frob:waive WALK001 reason="..."`
at each site (not blanket -- each reason names the specific bound) and a
new end-to-end regression test proving the waiver-suppression pattern.
gate:WALK is now 0 errors, 0 warnings, 36 waived (was 7 unwaived before
this change). Did NOT promote WALK001 WARN -> ERROR: the ticket's other
five families are not yet at zero, and promoting one code in isolation
was not asked for; a follow-up can promote once the whole gate group is
reviewed if desired.

The other five families are real, un-waived findings needing individual
doc/code review each of a different, unrelated shape (bind-or-reword doc
invariants, bind-or-reword negative-existence claims, wire-or-delete-or-
waive dead symbols) -- too large and too varied to review honestly in
this same pass without repeating T-2368's own mistake of assuming a
shared fix. Filed as scoped follow-up tickets with the measured counts
(see Filed below). LANG003's 27 findings need no new ticket: each one
already names its own tracking ticket (T-0329, T-3492, T-3493, T-3513)
-- it is a coverage-gap tracker whose findings are already dispositioned,
not un-filed work.

Filed:
T-3521 (DEAD001, 23 findings, 15 files)
T-3520 (INV003/INV004, 12 files each)
T-3519 (NEGEXIST001, 18 findings, 12 files)

### Changed
```
 src/frob/gates/_docstatus.py       |  1 +
 src/frob/gates/_gate_cache.py      |  1 +
 src/frob/lang/_support.py          |  1 +
 src/frob/refactor/_prose.py        |  3 ++
 src/frob/tickets/_models.py        |  1 +
 tests/test_walk_lint_gate.py       | 37 +++++++++++++++++++
 tickets/T-3483/ticket.md           |  2 ++
 tickets/T-3519/ticket.md | 64 +++++++++++++++++++++++++++++++++
 tickets/T-3520/ticket.md | 68 +++++++++++++++++++++++++++++++++++
 tickets/T-3521/ticket.md | 73 ++++++++++++++++++++++++++++++++++++++
 10 files changed, 251 insertions(+)
```

### Evidence
- `tests/test_walk_lint_gate.py::TestBoundedScopeWaiver::test_waived_bounded_glob_is_suppressed_end_to_end` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 4182 warning(s), 878 waived
- error-findings: AFFECT001@src/frob/gates/_docstatus.py, AFFECT001@src/frob/lang/_support.py, AFFECT001@src/frob/refactor/_prose.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3483, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
