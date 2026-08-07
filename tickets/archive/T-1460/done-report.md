## Done report

TICK009 scope-breadth cleanup pass, ledger-only (no source edits).

Before: 83 TICK009 nudges across 41 tickets (measured via `frob check
--only tickets`).

Narrowed the chronically-over-broad literal globs (docs/**, tests/**,
src/frob/**, src/**) on every QUEUED ticket carrying one, replacing each
with a genuinely smaller glob under the file-count threshold (docs/
commands/** [13 files], docs/audits/** [17], docs/design/*.md [21],
tests/integration/** [7], tests/test_tickets_lease.py [22],
tests/unit/gates/** [2], docs/modules/gates.md / tickets.md [1 each], or
a real domain subpackage like src/frob/perf/**). Left T-1400, T-1415,
T-1420 untouched (in-progress this wave, per the dispatch brief). One
ticket (T-1235) kept its tests/** glob because it already covers recorded
evidence and --remove refuses to orphan it (ScopeRemoveOrphansEvidence);
only its docs/** was narrowed.

After: 49 TICK009 nudges (measured the same way, same command).

Did NOT reach the <20 target. The remaining ~49 nudges are almost all
file-count-threshold warnings (not the unconditional chronic-literal
kind) on src/frob/gates/**, src/frob/app/**, src/frob/strata/**,
src/frob/tickets/**, tests/unit/**, tests/unit/strata/** -- every one of
these packages is a FLAT directory (no subpackages to narrow into: e.g.
src/frob/tickets has 33 .py files all at top level, src/frob/gates has
53), so there is no smaller-but-still-honest glob available without
either (a) enumerating the exact files each still-unstarted queued
ticket will touch, which is real per-ticket investigation outside a
ledger-only cleanup pass's scope, or (b) an actual package split
(an architecture change, not a ledger edit). Disclosing this rather than
guessing narrower globs that would misrepresent scope.

Also left the following as deliberately broad epic umbrellas without
narrowing further (their docs/tests globs were still narrowed where
literal-chronic, but their domain src globs were kept): T-0254, T-0260,
T-1135, T-1136, T-1137, T-1196, T-1198, T-1204, T-1238, T-1259, T-1382.
No frob:waive-style suppression mechanism exists for TICK009 (it is a
tickets.md-level WARN, not a code-adjacent gate finding) -- there is
nothing to attach a waive directive to, so these are disclosed here
instead.

### Changed
```
 docs/commands/sys.md                     |   6 ++
 docs/strata/surface.md                   |   7 ++-
 src/frob/strata/_sync_interface.py       |  25 ++++++--
 tests/unit/strata/test_sync_interface.py |  39 ++++++++++++
 tickets.md                               | 101 ++++++++++++++++++++++++++++++-
 5 files changed, 170 insertions(+), 8 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 201 warning(s), 729 waived
- error-findings: none (measured, zero errors)
