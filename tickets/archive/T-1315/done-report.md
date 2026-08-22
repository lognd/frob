## Done report

frob:no-behavior-change reason="docs-kind ticket: extends frob.toml [testing]'s rationale comment (no numeric floor changed -- unit_branch_cov/module_line_cov stay 75/70) plus a new design doc and an index link. No production code path changed, so there is no runtime behavior for a pytest test to exercise; the designated evidence (tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches, the T-0167 docs-ticket precedent) already passes and still passes, exactly what a no-behavior-change claim predicts."

RECOVERED (T-1934): this ticket's complete work -- design doc, frob.toml
extension, docs/index.md link, and the step-1 follow-up ticket -- was
finished on branch runner-wiring (commit 51782bc79) and committed there,
but the agent died before `frob ticket land` ever ran. T-1934 found it as
the confirmed leak. Recovered by extracting the three-file content commit
(51782bc79) verbatim rather than landing runner-wiring wholesale (56
commits, many unrelated tickets -- the T-1618 passenger guard would
correctly refuse it). The stranded done-report is honoured verbatim
below (its own measurements, dates, and design choice are unchanged);
only the recovery mechanics are new.

---

Original T-1315 Done report (runner-wiring, 2026-08-08), preserved
verbatim:

Designed and documented the TEST005/TEST006 floor ratchet schedule
(docs/design/test005-ratchet-schedule.md), extending -- not replacing --
frob.toml's existing T-0969 recalibration rationale comment (extended
in place, same [testing] block, dated 2026-08-08).

Measured the current state before writing any target, per the
coordinator's explicit instruction: `frob ticket epic T-1273` shows all
38 per-package burn-down children (T-1276..T-1313) archived done at
75/70; the committed frob-coverage.lock.json (2 days stale, the freshest
signal available to a sub-agent -- a full `make coverage` run is
explicitly coordinator-only per the playbook) shows 8/477 modules below
70%, 13 below 75%. Both are stated in the doc with their exact dates and
caveats, not carried forward as unverified fact. (Recovery note: these
numbers are from the ORIGINAL 2026-08-08 investigation and are stated in
docs/design/test005-ratchet-schedule.md with that date; nobody has
re-verified them at recovery time -- the doc's own "not fact, a trigger
condition" framing already covers this, and the schedule's own trigger
requires a FRESH measurement before step 1 can close, so the staleness
is structurally harmless to the schedule's own mechanism.)

Chose the documented-schedule shape over a per-package override table:
a per-package mechanism would need new TestPolicy fields and gate logic
(src/frob/gates/_models.py, src/frob/gates/__init__.py), out of this
ticket's declared scope, and the coverage lock's own existing per-module
ratchet (frob.toml's own rationale comment already cites it) already
gives any module that clears a higher bar a monotonic floor at its own
best-ever percentage -- the global number is the only thing that
actually needs to move.

The schedule is not just prose: step 1 (75/70 -> 80/75) is filed as a
real, closeable ticket (recovered as T-1953, the original
its now-orphaned original draft id never having reached main; scope frob.toml, parent
T-1273) with a concrete GIVEN/WHEN/THEN-shaped trigger (a coordinator-
run fresh make coverage + frob check --stamp-coverage, 0 TEST005
findings at the current floor, 0 modules below the next floor in the
fresh lock) and an explicit action list, including re-filing step 2
before step 1 closes -- so the schedule stays alive as each step lands,
rather than existing only as this document's own prose.

docs/index.md: added the new design doc to the Design-first-epics list
(DOC001 -- it must be linked from somewhere, not just describe itself).

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (docs-kind ticket, no own pytest surface -- T-0167 precedent, playbook section 5)

### Changed
```
 tickets/T-1315/done-report.md      | 79 ++++++++++++++++++++++++++++++++++++++
 tickets/T-1315/ticket.md           | 38 ++++++++++++++++--
 tickets/T-1953/ticket.md | 63 ++++++++++++++++++++++++++++++
 3 files changed, 177 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 7 error(s), 832 warning(s), 700 waived
- error-findings: COV003@tickets/T-0185, COV003@tickets/T-1351, COV003@tickets/T-1507, COV003@tickets/T-1512, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py, TICK006@tickets.md
