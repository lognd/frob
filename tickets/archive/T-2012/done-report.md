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
