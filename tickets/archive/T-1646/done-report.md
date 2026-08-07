## Done report

Ranked all files flagged by gate:LARGE (55 at start) by edit frequency
over the last 400 commits (`git log --format=%H --name-only -400`,
grouped/counted per path) rather than by raw line count, per the
ticket's own instruction. src/frob/gates/_fix_engine.py ranked highest
among genuinely splittable files (34 edits, 1940 lines) -- higher-ranked
paths (gates/__init__.py 63 edits/7627 lines, gates/_waive.py 34/1564,
app/ticket_runner/_land_cmd.py 33/2589, app/config.py 30/859) were
surveyed but each either needs a much larger, riskier multi-way split
(gates/__init__.py, already containing a dozen distinct DRIFT/COV/TEST/
SCOPE gate families interwoven with shared helper functions -- a correct
split there is a project of its own, not a one-file slice) or has no
honest seam (app/config.py is a single cohesive AppConfig pydantic model
with no internal grouping to cut along).

_fix_engine.py had a real, pre-existing seam: its own banner comments
already grouped every Tier-A auto-fix handler by rule id, and this repo
already has _fix_engine_tier_b.py/_fix_engine_tier_c.py as precedent for
exactly this kind of split (graph-driven vs diagnostic-line vs
artifact-sync handler families). Split into _fix_engine.py (graph-driven:
DOC007/DOC002/INV006-carry/TICK002 + the TIER_A_HANDLERS dispatch table),
_fix_engine_shared.py (FixApplied + manifest infra, split out specifically
to avoid a circular import between the other two handler-family modules),
_fix_engine_text.py (diagnostic-line: FMT001/SUPPRESS001/E501), and
_fix_engine_sync.py (derived-artifact-sync: REG010/REL002/SYS104/SYS100/
COV002/WAIVE004). Every function moved verbatim -- no behavior change,
confirmed by the touched test suite (test_gates_fix_engine.py 20/20,
test_gates.py's TestFixEngineTierA/TestAutofixManifest classes 29/29,
test_check_runner.py's fix-related tests 6/6, all passing).

Anticipated both side effects T-1420's split disclosed as landing-time
surprises: added the three new files to design/frob.strata's gates node
code= globs (both fs.read/fs.write lists) before running `frob sys
sync-interface`, which reports 0 drift; and every module carries the
SAME module-level INV006 waiver the original file had (moved verbatim,
noted explicitly as "carried forward, not a new claim" in each new
module's own waiver comment) since the exclusivity-vocabulary prose stays
with the code it describes in every split, never separated from it.

gate:LARGE: 55 -> 54 (unscoped, measured via `frob check --only archgate
--json` before/after). `frob check --land-parity` reports clean (0
unscoped errors) after the split.

Did NOT split (surveyed, no action taken beyond the priority scan
above): every other LARGE001 file. Filed the follow-up ticket
T-1651 ("LARGE001 remainder: 51 oversized files after T-1646's
one-file split") naming the still-open highest-priority candidates
(gates/__init__.py 63 edits, tickets/_land.py 29, tickets/_store.py 25,
strata/_selfconform.py 20, ~47 more) so this remainder is not silently
dropped the way T-1420's and T-1204's were -- per this ticket's own
explicit instruction and the standing T-1648 lesson about disclosed
unfinished work needing a real follow-up ticket, not just prose.

No waivers were added in this round -- the one file split this round had
a genuine seam, so none needed disposing by waiver; the follow-up ticket
inherits the same "find the seam or waive with a specific reason" method
for whichever of the remaining 51 files it works.

### Changed
```
 design/frob.strata                   |    4 +-
 docs/modules/gates.md                |   26 +-
 src/frob/arch/_mayraise.py           |    2 +-
 src/frob/gates/_fix_engine.py        | 1429 +---------------------------------
 src/frob/gates/_fix_engine_shared.py |  135 ++++
 src/frob/gates/_fix_engine_sync.py   |  684 ++++++++++++++++
 src/frob/gates/_fix_engine_text.py   |  689 ++++++++++++++++
 src/frob/release/__init__.py         |    4 +-
 src/frob/tickets/_land_git_ops.py    |    4 +-
 tests/test_gates.py                  |   60 +-
 tests/test_gates_fix_engine.py       |   25 +-
 tickets.md                           |   82 +-
 12 files changed, 1683 insertions(+), 1461 deletions(-)
```

### Evidence
- `tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestAutofixManifest::test_apply_tier_a_fixes_clears_manifest_on_clean_finish` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 2725 warning(s), 848 waived
- error-findings: none (measured, zero errors)
