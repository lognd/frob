---
id: T-3275
title: 'PORT001 cannot see project identity hardcoded outside the four detector packages:
  frob coverage''s src/frob target is invisible to dogfooding by construction'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_detector_scope.py
- src/frob/testing/_coverage_refresh.py
- src/frob/gates/_port_selfcheck.py
- docs/modules/gates.md
- docs/modules/testing.md
- tests/unit/gates/test_port_selfcheck.py
- tests/test_coverage.py
- tests/unit/gates/test_detector_scope.py
- tickets/T-draft-24c487c8/ticket.md
- tickets/T-draft-8485751c/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_port_selfcheck.py
  reason: PORT001's own scan-population call site must switch from DETECTOR_PACKAGE_ROOTS
    to the new repo-wide identity-hardcoding population; cannot widen PORT001 without
    editing its own call site
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/gates.md
  reason: PORT001's scope-derivation docstring is frob:doc-anchored there; must update
    to describe the new repo-wide population
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/testing.md
  reason: native_coverage_refresh's cov_target resolution behavior is frob:doc-anchored
    there
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/gates/test_port_selfcheck.py
  reason: must-fire/must-stay-quiet fixtures for the widened PORT001 scan population
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_coverage.py
  reason: 'third fixture: frob coverage in a non-frob-named repo measures that repo''s
    own package'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/gates/test_detector_scope.py
  reason: unit test for the new tracked_repo_python_files function cited in its frob:tests
    directive
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tickets/T-draft-24c487c8/ticket.md
  reason: follow-up ticket filed from this ticket's own work, touched via frob ticket
    new
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tickets/T-draft-8485751c/ticket.md
  reason: follow-up ticket filed from this ticket's own work, touched via frob ticket
    new
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER QUESTION 2026-08-28: "frob coverage hardcodes 'src/frob'; how is our
dogfooding not catching that?" This ticket is the answer and the fix.

THE DEFECT THAT PROMPTED IT (reported from real consumer use, ../diax
FROBLEMS.md F-011): `src/frob/testing/_coverage_refresh.py:100`

    _DEFAULT_COV_TARGET = "src/frob"

A consumer repo running `frob coverage` measures FROB'S package path, gets "No
data was collected", and the run is marked DEGRADED. The CLI exposes no
--cov-target.

WHY DOGFOODING CANNOT CATCH THIS, EVER. `"src/frob"` is CORRECT for frob. Every
dogfood run passes by construction. The value is only wrong in a repo we never
run in. No amount of running frob on frob will surface it -- this is a
structural blind spot, not a missed test.

WHY THE GATE BUILT FOR THIS BLIND SPOT DID NOT FIRE. PORT001
(`src/frob/gates/_port_selfcheck.py`, T-2388) exists precisely to catch "a rule
that hardcodes THIS project's own identity instead of resolving it from
declared config". It scans `DETECTOR_PACKAGE_ROOTS`
(`src/frob/gates/_detector_scope.py:72`):

    src/frob/check/   src/frob/gates/   src/frob/strata/   src/frob/vet/

`_coverage_refresh.py` is in `src/frob/testing/`. Not scanned.

That scope was not arbitrary -- T-2466 derived it by COUNTING
`Violation(`-constructing modules per package, and excluded `arch/` on that
same evidence. It is a sound rule for "where do detectors live". But the defect
class is "WHERE DOES PROJECT IDENTITY GET HARDCODED", and those two sets are
different. `testing/` constructs no violations and carries exactly the
hardcoded identity PORT001 was built to find.

The gate's own docstring foreshadows this: it records that `_env_var_docs.py`
and `_root_asset_dirs.py` "both silently matched NOTHING against a
differently-named/laid-out project ... the gate is present, listed, and
documented, while enforcing nothing off-repo." Same failure mode, one directory
over.

CURRENT SCALE, measured 2026-08-28: 31 files under `src/` contain the literal
`"src/frob`. T-2384's body recorded 22. It has grown since the gate shipped,
which is what an under-scoped guard looks like over time.

DENOMINATOR DISCIPLINE, inherited from this gate's own docstring and NOT to be
ignored: PORT001 logs its scanned scope alongside its count on every run
because a count without its denominator is the silent-zero class wearing a
different hat. Whatever scope you land, keep that property -- a number that can
be quoted without its scope will be.

WHAT TO BUILD:
  1. Fix `_DEFAULT_COV_TARGET` so `frob coverage` resolves the target from the
     consumer's own config (the project's package layout, or the
     `[[test.runner]]` environment), not from a literal. Expose an override.
  2. Re-scope PORT001 by the RIGHT question. `DETECTOR_PACKAGE_ROOTS` answers
     "is this a detector"; this rule needs "can this file embed project
     identity", which is a broader and differently-derived set. Do NOT simply
     append `testing/` -- that fixes one instance and leaves the class. Derive
     the new scope by measurement and state the method, as T-2466 did.
  3. Do NOT invent a second detector architecture. T-2388's directive stands:
     PORT001 and LEXCHECK001 deliberately share a shape.

REPORT, DO NOT FIX HERE: of the 31 files, how many are genuine violations
versus legitimate self-references (frob's own tests, its own selfconform rules,
docstrings quoting a path). File the real ones as their own tickets with the
count stated. A gate that widens onto 31 findings and waives 25 of them has
learned nothing.

MUST-FIRE FIXTURE: a `src/frob/testing/`-shaped module hardcoding the package
path is flagged.
MUST-STAY-QUIET FIXTURE: a legitimate self-reference (frob's own
selfconformance rule that must name frob) is not flagged, and the existing
gates/check/strata/vet coverage does not regress.
THIRD FIXTURE: `frob coverage` in a repo whose package is NOT `frob` measures
that repo's package.

ACCEPTANCE
- `frob coverage` works in a consumer repo; state how the target is resolved.
- PORT001's scope derived by a stated method, not by appending one directory.
- The scanned-scope log line preserved.
- A stated count of real violations found by the widened scope, filed
  separately.
