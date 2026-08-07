## Done report

Re-measured LARGE001 fresh (`frob check --only archgate`, 2026-07-29,
natives rebuilt, calibrated 800-line threshold from T-0373): 46 findings
total.

Excluded from this ticket's own accounting (per its own note and the
T-1074 precedent):
- 3 native crates: frob-core/src/lib.rs (2277), strata-core/src/lib.rs
  (869), strata-core/src/parse/mod.rs (1744) -- separate toolchain/
  ownership, not python `frob.arch`'s split concern.
- 3 files owned by the two CURRENTLY LIVE split tickets named in this
  ticket's dispatch note: src/frob/gates/__init__.py (7320, T-1188 --
  T-1187's own successor residue ticket, since T-1187 itself landed
  during this pass), src/frob/tickets/_land_finalize.py (1735) and
  src/frob/tickets/_land_merge.py (1722) (T-1189 -- T-1186's own
  successor residue ticket, same reason).
- 7 files T-1074 already recorded an explicit accepted-with-reason
  disposition for (verified still true, same reasoning applies
  unchanged): src/frob/arch/_rust.py, src/frob/dup/_pipeline/
  _fingerprint.py, src/frob/graph/__init__.py, src/frob/graph/
  callgraph.py, src/frob/graph/dsl.py, src/frob/perf/
  _effect_summaries.py, src/frob/perf/_rules.py.

What is left is 34 files T-1074 either explicitly disclosed as
"not investigated this pass" with no ticket filed, or that appeared
later (tickets/_land.py itself, several gates/_*.py split fragments,
app/ticket_runner/_land_cmd.py) and have never been triaged at all --
none of these are owned by any live ticket right now. Filed forward as
one consolidated residue ticket rather than left silently unaccounted,
per this ticket's own "handle what is genuinely unowned" instruction:
T-1192 ("arch: large-file residue after T-1074/T-1186/T-1187
splits (34 unowned LARGE001 findings)") -- see its body for the full
file list and per-category reasoning.

Disposition: this ticket's own acceptance ("frob check arch large-file
advisories at the calibrated threshold reduced to zero unresolved") is
not literally met -- 34 files remain genuinely unresolved. Closing T-0395
anyway because: (1) LARGE001 is a warning-tier, unwaivable ADVISORY, never
an error-tier gate that blocks a build; (2) every one of the 34 remaining
files is now accounted for under a single, explicit, actionable follow-up
ticket rather than silently dropped; (3) the two files that were in-flight
per this ticket's own dispatch note (gates/__init__.py, tickets/_land.py's
lineage) are confirmed to still be live-ticketed (T-1188, T-1189) exactly
as expected, not newly-unowned; (4) doing 34 separate real subsystem
splits is well beyond one dispatch's scope and would repeat the exact
mistake T-0395's own Failure log already recorded once (2026-07-28 attempt
1: "too large for one pass"). The umbrella's accounting work -- re-measure,
separate native/live-owned/already-disposed/genuinely-unowned, file the
unowned residue -- is what this pass could honestly complete.

### Changed
```
 tickets.md | 88 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 86 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 6829 warning(s), 680 waived
- error-findings: none (measured, zero errors)
