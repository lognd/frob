---
id: T-1315
title: 'TEST005 floor ratchet-up schedule: 75/70 is a waypoint, not a surrender'
state: done
kind: docs
origin: human
created: '2026-07-29'
priority: low
parent: T-1273
tier: ticket
sprint: null
runs_last: false
scope:
- frob.toml
- docs/design/test005-ratchet-schedule.md
- docs/index.md
- tickets/T-1953/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: The ratchet schedule this ticket designs lives against frob.toml [testing]s
    existing recalibration comment (the exact anchor its own acceptance criteria name)
    plus a new design doc for the schedule itself -- kept as two concrete files, no
    glob, per T-1866.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/test005-ratchet-schedule.md
  reason: The ratchet schedule this ticket designs lives against frob.toml [testing]s
    existing recalibration comment (the exact anchor its own acceptance criteria name)
    plus a new design doc for the schedule itself -- kept as two concrete files, no
    glob, per T-1866.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/index.md
  reason: recovering the stranded runner-wiring branch's own scope additions (docs/index.md
    DOC001 link, the step-1 draft ticket the done-report filed) alongside the original
    frob.toml/design-doc scope
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-draft-fd2c5ba4/**
  reason: recovering the stranded runner-wiring branch's own scope additions (docs/index.md
    DOC001 link, the step-1 draft ticket the done-report filed) alongside the original
    frob.toml/design-doc scope
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tickets/T-draft-fd2c5ba4/**
  reason: T-draft-fd2c5ba4 never existed on main (it was on the abandoned runner-wiring
    branch); recreated as T-1953 during recovery
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1953/**
  reason: T-draft-fd2c5ba4 never existed on main (it was on the abandoned runner-wiring
    branch); recreated as T-1953 during recovery
  actor: logan
  at: '2026-08-10'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN a package that has reached zero TEST005 findings at 75/70 WHEN the ratchet
    schedule lands THEN that package's effective floor is documented to step toward
    90/85 (per-package override or schedule), not remain frozen at the recalibrated
    minimum
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: GIVEN frob.toml's existing recalibration rationale comment WHEN the ratchet
    design is written THEN it explicitly cites and extends that rationale rather than
    contradicting or duplicating it
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
anchor: false
anchor_reason: null
---
frob.toml [testing] recalibrated unit_branch_cov=75 / module_line_cov=70
on honest TEST005 attribution data (T-1235 fixed subprocess + pool-worker
coverage recording); the in-file rationale comment documents why these
specific numbers were chosen as the current floor, not a permanent
target.

Design a ratchet schedule: once a package (T-1276..T-1313 in this epic)
reaches zero TEST005 findings at 75/70, its floor should step up toward
90/85 rather than stay parked at the recalibrated minimum -- otherwise
the recalibration silently becomes a ceiling. Decide and document
(either in frob.toml as per-package floor overrides, or as a documented
schedule/policy the gate reads) how and when a cleared package's floor
increases, and how regressions below the new floor are caught.

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
