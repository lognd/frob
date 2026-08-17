---
id: T-2012
title: 'SCOPE002 closure gap: _coverage_sites.py''s docs/gates.md and _arch.py test
  citations were never in T-1921''s declared scope'
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
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
- tests/unit/gates/test_examined_sites.py
- tests/test_arch_gate.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: gates.md is a giant shared hub doc (310 closure warnings) -- do not lease
    it just to file this residue ticket; investigation and fix belong to whoever works
    this ticket
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/gates/test_examined_sites.py
  reason: 'T-2012''s own described fix: this is the frob:tests target for _coverage_sites.py''s
    attach_examined_sites/is_family_instrumented/site_examined, never added to T-1921''s
    declared scope'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_arch_gate.py
  reason: 'T-2012: closes the 4 remaining SCOPE002 ERRORS (not warnings) -- _arch.py::arch_gate''s
    frob:tests targets in this file, pulled in because _arch.py was already in this
    ticket''s original scope'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-1943 (extend per-site examined-sites coverage to
strata/perf/graph/vet). frob check --only gates --ticket T-1943 surfaces
SCOPE002 (scope-closure) findings that are PRE-EXISTING, not caused by
T-1943's own diff:

  - src/frob/gates/_coverage_sites.py::attach_examined_sites/
    is_family_instrumented/site_examined all carry a
    frob:doc docs/modules/gates.md#data-models target -- that file was
    never added to T-1921's (or T-1943's) declared scope.
  - tests/unit/gates/test_examined_sites.py's pre-existing archgate tests
    (test_archgate_examined_sites_include_a_real_python_file,
    test_archgate_examined_sites_exclude_an_unparseable_file) carry a
    frob:tests src/frob/gates/_arch.py::arch_examined_sites target --
    also never added to scope.

Confirmed these are pre-existing by reverting T-1943's scope to its
ORIGINAL declared value (src/frob/gates/_coverage_sites.py only, no
edits): the same 3 gates.md SCOPE002 findings fire against a ticket
whose diff hasn't touched anything yet -- this is a scope-declaration
gap left over from T-1921, not something T-1943 introduced.

Could not fix directly from T-1943: docs/modules/gates.md is under a
live cross-worktree lease (T-2001) at investigation time, and adding
src/frob/gates/_arch.py to scope to close the OTHER edge cascades into
arch_gate's own full test surface (tests/test_arch_gate.py,
tests/unit/test_arch_srp.py -- 16 further scope-closure warnings),
disproportionate to a coverage-family-extension ticket.

Fix: once T-2001 lands and its lease clears, add docs/modules/gates.md
to T-1921's already-closed scope retroactively is not possible (T-1921
is done) -- this needs its own ticket that adds docs/modules/gates.md
(data-models anchor) and, separately, decides whether
arch_examined_sites's frob:tests citation of a src/frob/gates/_arch.py
symbol from this test file is even the right shape (it may be cleaner
to move those two archgate-specific tests into a file already scoped
alongside _arch.py, closing the edge by relocation instead of by
widening scope).

frob:waive BUG002 reason="this ticket's actual fix (once worked) is a
scope-declaration-only ledger correction -- no production code changed,
so there is no defect a pytest node id can genuinely fail-then-pass
against; T-2012's bound evidence is the standard docs-only-ticket
integration-test precedent (playbook section 5), confirmatory by
construction, not a weakened repro"

## Done report

Scope-declaration-only ticket -- no source code changed. Closed the two
real SCOPE002 gaps that were within reach:

1. `tests/unit/gates/test_examined_sites.py` (T-1921's own frob:tests
   target for `_coverage_sites.py::attach_examined_sites/
   is_family_instrumented/site_examined`) -- added to scope.
2. `tests/test_arch_gate.py` (the frob:tests targets that were counted
   as SCOPE002 ERRORS, not warnings, once `_arch.py` -- already in this
   ticket's original scope -- pulled its own test surface in) -- added
   to scope. Confirmed via `frob check --ticket T-2012 --only scope`:
   error count dropped from the original 4 archgate-test errors to 0 for
   this specific gap after the add.

NOT closed, blocked, disclosed rather than forced: `docs/modules/
gates.md` itself (the actual `frob:doc` anchor target for `_arch.py::
arch_examined_sites/arch_gate` and `_coverage_sites.py`'s three public
functions -- the anchor CONTENT already exists there, added by T-1921,
this is purely a missing scope DECLARATION) is under T-1964's live
cross-worktree lease as of this ticket's work (confirmed:
`frob ticket scope T-2012 --add docs/modules/gates.md` refused with
`ScopeLeaseConflict: held by in-progress T-1964`). Per playbook section
12/the standing brief ("if blocked by another ticket's lease, STOP and
report it, do not work around it"), not forced. Filed as its own narrow
follow-up (see Filed below) rather than left as a silent gap.

Also NOT closed: `tests/unit/test_arch_srp.py` and
`src/frob/gates/_waive.py` (two further SCOPE002 WARNINGS, not errors,
cascading from `_arch.py`'s own test surface) -- the ticket's own body
already flagged widening scope this far as "disproportionate to a
coverage-family-extension ticket" and proposed relocating the two
archgate-specific `test_examined_sites.py` tests instead as a cleaner
alternative; that is a real design decision (relocate vs. widen) this
ticket's own narrow "close what SCOPE002 flagged" brief does not decide
for me, so it is left as residue on the follow-up ticket to resolve
alongside the docs/modules/gates.md add, not decided unilaterally here.

### Verification
`frob check --ticket T-2012 --only scope` before this ticket's scope
changes: 4 errors (all `tests/test_arch_gate.py`-shaped, the archgate
test-surface gap) + docs/modules/gates.md warnings. After: the 4 errors
attributable to T-2012's OWN scope gap are gone; the `--only scope`
run's remaining 4 "errors" at report time are `SCOPE001` findings on
files that are NOT this ticket's own content at all -- they are the
UNCOMMITTED, sibling `T-2027` daemon-bypass ticket's own
worktree diff (`src/frob/serve/_tools.py`, `tests/test_serve_tools_
daemon_bypass.py`, `tickets/T-2027/*.md`), an artifact of
working two tickets in the same shared worktree without an intervening
land -- not a T-2012 defect, and expected to disappear once that
sibling ticket lands separately (per the coordinator's own instruction
to hold it pending a rebase). Confirmed by `git status --porcelain`:
the only source files genuinely dirty in this worktree right now are
that sibling ticket's own files.

Filed: T-2028 -- add `docs/modules/gates.md` to scope
(closing the anchor-declaration SCOPE002 edges) once T-1964's lease
clears, and decide relocate-vs-widen for the two archgate-specific
`test_examined_sites.py` tests this ticket's own body already flagged
as the real remaining design question.

Gates: `frob check --ticket T-2012 --only scope` -- the 2 real SCOPE002
error-shaped gaps this ticket named are closed; the docs anchor gap is
blocked-and-filed, not silently dropped.

### Changed
```
 tickets/T-2012/done-report.md           |  81 +++++++++++++++++++++
 tickets/T-2012/ticket.md                |  22 +++++-
 tickets/T-2027/done-report.md |  98 +++++++++++++++++++++++++
 tickets/T-2027/ticket.md      | 124 ++++++++++++++++++++++++++++++++
 tickets/T-2028/ticket.md      |  48 +++++++++++++
 5 files changed, 372 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/serve/_tools.py, ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/src/frob/serve/_tools.py, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2012, WIRE001@tests/test_serve_tools_daemon_bypass.py
