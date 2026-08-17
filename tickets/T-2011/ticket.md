---
id: T-2011
title: Wire perf/strata/graph/vet examined-sites reporters (T-1943) into a real WAIVE004
  consumer
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- tests/unit/test_waive004_perf_guard.py
- docs/modules/gates.md
- src/frob/gates/_coverage_sites.py
- src/frob/gates/_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_waive004_perf_guard.py
  reason: 'T-2011: new standalone test file for the perf-family WAIVE004 guard (tests/test_gates.py
    is under T-1959''s live lease)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-2011: WAIVE004 section needs its perf-family guard documented alongside
    T-1942''s archgate write-up'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: 'T-2011 close is blocked by LiveTrackerCited: the WIRE001 waivers in these
    two files cite follow_up=T-2011 as their live tracker; must re-point to the T-2057
    successor before this ticket can close'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_arch.py
  reason: 'T-2011 close is blocked by LiveTrackerCited: the WIRE001 waivers in these
    two files cite follow_up=T-2011 as their live tracker; must re-point to the T-2057
    successor before this ticket can close'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_examined_perf_site_is_deleted
- tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_unexamined_perf_site_refuses
- tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_perf009_is_excluded_from_the_guard
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1943 extended frob.gates._coverage_sites' per-site examined-sites
substrate from archgate-only to perf/strata/graph/vet
(_perf_examined_sites/_strata_examined_sites/_graph_examined_sites/
_vet_examined_sites), matching T-1904's own investigation of which
families the 55-waiver incident actually hit. Same posture T-1921 took
for archgate: substrate only, no production caller wired in the same
change (the coordinator's standing instruction against doing both in
one diff, per the incident history).

T-1942 already wired archgate's examined-sites into
_drop_untrustworthy_mass_stale_candidates as
_drop_unexamined_archgate_candidates
(src/frob/gates/_fix_engine_sync.py). This ticket is the same shape for
the four new families: add an additive, per-site guard using
site_examined(stats, family, file) for each of "perf"/"strata"/"graph"/
"vet", alongside (never instead of) the existing archgate guard and the
absolute/proportional count guards. Refuse on any uncertainty, same
regression-lock posture as T-1942's own acceptance test.

## Done report

Investigated all four T-1943 examined-sites families (perf/strata/graph/vet)
by reading the actual code path from rule violation to Violation.file, not
by trusting family names. Only perf is soundly wireable; the other three
are left deliberately unwired with the code-level reason recorded.

perf (WIRED): perf_gate's rules (PERF001-008, PERF010-014) are all fed
from frob.perf.perf_rules(snapshot, parsed), where `parsed` is exactly the
candidate/parse-success set _perf_gate_candidate_paths/_perf_gate_parse_files
compute -- matching what _perf_examined_sites (frob.gates._coverage_sites)
independently re-derives. PERF009 is excluded from _PERF_RULE_IDS: it comes
from a precomputed `.frob/perf/ratchet_findings.json` artifact
(ratchet_violations), never from this run's own parse pass, so the
examined-sites substrate cannot honestly vouch for it.

strata (left unwired): sys_gate's SYS001-004/SELFAUDIT001 violation sites
do not correspond to .strata design-file identity. SYS001 (_sys001_check_edge)
reports the CODE site of the directive via _site_from_edge_origin; SYS002
(_sys002) constructs a synthetic "design/<kind>/<id>" string; SYS003
(_sys003_one_model) reports check_import_conformance's own violation.file
(a code import site); SELFAUDIT001 (_selfaudit_violation,
src/frob/gates/_sys_selfaudit.py:64) always reports the whole design_dir
CONSTANT, never a per-file site. Only SYS004 reports a real .strata path
(error.path), and it fires exactly when that file FAILED to load -- by
_strata_examined_sites' own construction, a failed-load file is never a
member of the examined set. No rule in this family has a violation site
that lines up with what the strata reporter tracks.

graph (left unwired): frob.graph.build_graph's GraphSnapshot backs dozens
of unrelated gate families (SYS00x, DRIFT, COV, REF, ...) with
heterogeneous violation-site shapes. No single rule family "owns" it the
way arch_gate/perf_gate own their rule ids, so there is no sound
_graph_rule_ids to define -- matches T-1904's own prior assessment.

vet (left unwired, and a real inaccuracy found): _vet_examined_sites' own
docstring names OPAQUE001 as this family's consumer, but opaque_gate
(src/frob/gates/_opaque.py:110) does not call scan_file_capabilities at
all -- it calls _opaque_indirection_findings, a scanner its own module
docstring says is DELIBERATELY DISJOINT from the scan_file_capabilities
universe (docs/design/capability-evasion-taxonomy.md's two-universe split).
scan_file_capabilities is actually consumed by frob.strata._selfconform
(folded into SELFAUDIT001, same design_dir-constant site problem as
strata above) and by frob.vet._capability_scan.py's
_aggregate_capabilities, which scans a THIRD-PARTY dependency's extracted
source tree (source_dir), never this repo's own `root` --
_vet_examined_sites(root) walks this repo's own tracked files, so even
that usage's file-identity space does not match. No live rule's
violation site corresponds to what _vet_examined_sites tracks. This
docstring inaccuracy in src/frob/gates/_coverage_sites.py is a real,
pre-existing finding, left uncorrected (out of this ticket's declared
scope, src/frob/gates/_fix_engine_sync.py) -- filed as a new ticket
instead of hand-fixed.

Implementation (src/frob/gates/_fix_engine_sync.py): added _PERF_RULE_IDS
and _drop_unexamined_perf_candidates, mirroring T-1942's
_archgate_rule_ids/_drop_unexamined_archgate_candidates exactly --
additive-only (can only remove a candidate a prior guard already proposed
to retire, never add one back), grants nothing outside _PERF_RULE_IDS.
Wired into _waive004_verified_candidates immediately after the archgate
guard, so all four guards (mass-invalidation, degraded-run, archgate,
perf) stack.

Repro proof (playbook rule 7, section 0 item 6): before adding the perf
guard, `test_unexamined_perf_site_refuses` FAILS -- a perf-rule waiver on
a file with no tree-sitter grammar (never reached by the parse pass) was
still deleted by the pre-T-2011 code (only the mass-invalidation/
degraded-run guards existed, neither catches a single unexamined
candidate). Verified directly: temporarily replaced
src/frob/gates/_fix_engine_sync.py with `git show HEAD:...` (i.e. this
worktree's pre-fix commit) and ran
`pytest tests/unit/test_waive004_perf_guard.py -q` -- 1 failed
(test_unexamined_perf_site_refuses: AssertionError, applied contained a
FixApplied instead of []). Restored the fix; all 3 tests pass.

Deletion safety (brief requirement 4) is an ARGUMENT, not a measurement.
This change was NEVER run against this repo's own real frob:waive
directives -- fix_waive004_stale_waiver was exercised only inside the
new/existing unit tests against synthetic tmp_path fixtures. No waiver
count was taken before/after against the live tree, and none should be
inferred from anything in this report: no waiver in this repo's real
tree was deleted, added, or touched by this ticket's work, and this
report makes no claim otherwise. Given this repo deleted 55 live
waivers once on unsound liveness reasoning (T-1579), that distinction is
worth being explicit about rather than letting a report read as though a
count was taken.

The safety claim instead rests on the STRUCTURE of the change: both new
guards (_drop_unexamined_perf_candidates here, and the pre-existing
archgate one from T-1942) are strictly subtractive filters stacked AFTER
the two pre-existing guards (mass-invalidation, degraded-run) in
_waive004_verified_candidates -- each can only REMOVE a (file, line,
rule) candidate a prior stage already proposed to delete, and neither
has any code path that adds a candidate back. That ordering is what
makes the fully-wired pipeline provably no less conservative than before
this ticket landed: it can refuse more deletions than before, it cannot
newly permit one it would not already have permitted.

Gates: `frob check --only test --ticket T-2011` -- 0 errors, 25 warnings
(all pre-existing, unrelated: TEST003/TEST006/TEST014 baseline noise).
`frob check --land-parity` (589s budget) reported 2 unscoped errors
(F401 in tests/test_gates_fmt_directives.py and
tests/unit/test_tickets_evidence_only_scope.py) -- verified these are
NOT a regression from this ticket: both files are untouched by this
diff (`git status --porcelain` on them is empty against my commit), and
`diff --strip-trailing-cr` against `git show <base>:<path>` (base =
cea267451, this worktree's cut point from main) shows byte-identical
content once a CRLF/LF artifact (this checkout has core.autocrlf=true)
is discounted -- these two F401s are pre-existing on main, orthogonal to
this ticket's scope, not introduced or hidden by this change.

Filed: T-2056 for the _vet_examined_sites docstring inaccuracy
(OPAQUE001 claim) described above (renumbers at land; out of T-2011's
declared scope to fix directly). Also filed T-2057 (the strata/
graph/vet WAIVE004-wiring successor) so the WIRE001 waivers in
src/frob/gates/_coverage_sites.py/_arch.py that cited follow_up="T-2011"
had a live tracker to re-point to before this ticket's own close.

docs/modules/gates.md was in this ticket's scope (needed for the WAIVE004
section write-up above) and was reported as blocking two other tickets'
own scope leases for several hours -- landing this ticket promptly is
what releases that lease, not a scope narrowing after the fact.

Gates: frob check --only test --ticket T-2011 clean (0 errors).
frob check --land-parity: 2 pre-existing, unrelated F401 findings,
verified not a regression from this diff (see above); no error
attributable to this ticket's own scope.

### Changed
```
 docs/modules/gates.md                  |  62 ++++++++++++
 src/frob/gates/_fix_engine_sync.py     |  84 +++++++++++++++-
 tests/unit/test_waive004_perf_guard.py | 174 +++++++++++++++++++++++++++++++++
 tickets/T-2011/ticket.md               |  21 +++-
 tickets/T-2056/ticket.md     |  61 ++++++++++++
 5 files changed, 398 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_examined_perf_site_is_deleted` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_unexamined_perf_site_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard::test_perf009_is_excluded_from_the_guard` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, CLAUDE001@.claude/hooks/sync-claude-config.py, F401@/home/logan/projects/frob/.claude/worktrees/t2011-waive004/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2011-waive004/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design
