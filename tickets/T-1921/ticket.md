---
id: T-1921
title: Per-site analysis-coverage substrate for WAIVE004 escape (T-1904 successor)
state: done
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_models.py
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
- src/frob/arch/__init__.py
- src/frob/arch/_models.py
- tests/test_gates.py
- tests/unit/gates/test_examined_sites.py
- docs/modules/gates.md
- docs/modules/arch.md
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_fix_engine_sync.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: src/frob/gates/_models.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tests/test_gates.py
  reason: clear pre-declared scope to avoid lease collision at land time with concurrently-worked
    gates files; the future implementer will re-scope with frob ticket scope --add
    at start time per normal workflow
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_models.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_arch.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/arch/__init__.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/arch/_models.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/gates/test_examined_sites.py
  reason: 'per-site analysis-coverage substrate: GateStats gains examined_sites; populated
    for the ARCH family via analyze_project/arch_gate; a new gates/_coverage_sites.py
    enrichment module + query helper (avoids touching gates/__init__.py, leased by
    T-1929); new regression test file'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001/COV001 doc-anchor closure for the changed ArchResult/GateStats/arch_gate
    public symbols
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/modules/arch.md
  reason: AFFECT001/COV001 doc-anchor closure for the changed ArchResult/GateStats/arch_gate
    public symbols
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/commands/check.md
  reason: AFFECT001 closure for analyze_project's memoization doc anchor
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_uninstrumented_family_reports_not_examined
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_family_reports_true_for_a_known_site
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_family_reports_false_for_an_unexamined_site
- tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_but_empty_family_still_reports_false_for_any_site
- tests/unit/gates/test_examined_sites.py::TestIsFamilyInstrumented::test_absent_family_is_not_instrumented
- tests/unit/gates/test_examined_sites.py::TestIsFamilyInstrumented::test_present_empty_family_is_instrumented
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_archgate_examined_sites_include_a_real_python_file
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_archgate_examined_sites_exclude_an_unparseable_file
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_preserves_examined_sites_a_prior_caller_already_attached
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed from T-1904's own investigation (2026-08-09). T-1904's acceptance
criteria required per-SITE analysis-coverage tracking -- proof that the
specific waived (file, line, rule) site was actually re-analyzed in a
given run, not just that the rule produced a finding SOMEWHERE (the
already-falsified T-1579/_rule_has_live_finding shape that deleted 55
live waivers).

WHAT WAS INVESTIGATED. `GateReport`/`GateStats` (src/frob/gates/_models.py)
today carry only violations, waived violations, and per-gate counts/
timing/skipped-stage names -- there is no notion anywhere in the gate
substrate of "which files/sites did gate X actually visit this run".
Adding that honestly requires each gate FAMILY's own implementation (AST
walkers, native-backed checks, doc/registry scanners -- dozens of
independent modules under src/frob/gates/) to report its own examined-site
set, then plumbing that set through `run_gates`'s merge into `GateReport`,
then having `_drop_untrustworthy_mass_stale_candidates`
(src/frob/gates/_fix_engine_sync.py) consult it per candidate before ever
relaxing the count guards. That is a substrate change touching every gate
implementation, not a guard tweak -- exactly what T-1904's own body
predicted ("materially larger... a capability the gate substrate does not
currently have") and too large for a single ticket's scope.

WHAT T-1904 ITSELF DID. Re-applied the T-1579 branch's docstring note
(commit fc8f5bab9) onto `_drop_untrustworthy_mass_stale_candidates` in
`src/frob/gates/_fix_engine_sync.py`, on top of the landed refactor --
the "ALSO OWED" item T-1904's body named. No behavior changed; both count
guards (absolute and proportional) remain unconditional refusals, and the
standing regression lock
(`tests/test_gates.py::TestWaive004DegradedRunGuard::
test_mass_invalidation_with_live_finding_elsewhere_still_refuses`) is
untouched and still passing.

SCOPE FOR THIS TICKET. Design and land the per-site analysis-coverage
substrate:
- A shared `examined_sites` (or per-file) reporting contract every gate
  family can optionally populate, added to `GateStats`/`GateReport`.
- At least the WAIVE004-relevant gate families populate it for real
  (start with whichever families most of today's live `frob:waive`
  directives target -- arch/strata/perf/graph/vet, the exact families the
  55-waiver incident hit).
- `_drop_untrustworthy_mass_stale_candidates` gains a THIRD, additive
  check: a candidate's own site must appear in the examined set for its
  rule's owning gate family this run, in addition to (never instead of)
  the existing absolute/proportional guards -- still refuse on any
  uncertainty, per T-1904's acceptance test (a waiver whose site the
  analysis did not cover must never be deletable).
- Prove the acceptance property with a new regression test: fabricate a
  run that examined some but not all sites of a mass-stale rule and show
  the guard still refuses for the unexamined site.

Do not ship an automatic retirement path until the coverage substrate
itself has full field coverage across every gate family a live
`frob:waive` can target -- a partial substrate that "looks done" for a
few families is the same trap the 55-waiver incident was.

## Done report

Read T-1904's ticket and Done report first, per this ticket's brief.
T-1904 confirmed GateReport/GateStats carried no per-site "examined"
concept at all, and building one honestly requires each gate family's
own implementation to report an examined-site set -- a substrate change
spanning dozens of independent gate modules, disproportionate for one
ticket. This ticket built the SUBSTRATE ONLY, per the coordinator's
explicit instruction not to wire any automatic waiver-retirement
consumer on top of it in this change -- that is precisely the shape
that let the falsified T-1579 escape (_rule_has_live_finding) delete 55
live waivers, and repeating "build the substrate and the consumer in
one change" was named as the exact trap to avoid.

WHAT SHIPPED:

- `GateStats.examined_sites: Mapping[str, frozenset[str]]`
  (src/frob/gates/_models.py) -- keyed by gate family name (the same
  string `--only <family>` accepts). A family key absent means "not
  instrumented"; this substrate makes no claim. A family key present
  but a file not a member means "instrumented, this run did not reach
  it". Only a family whose reporter positively recorded a file counts
  as examined.

- `src/frob/gates/_coverage_sites.py` (new): `site_examined(stats,
  family, file) -> bool` (the ONE sanctioned way to ask the coverage
  question), `is_family_instrumented(stats, family) -> bool`
  (distinguishes "not instrumented" from "instrumented, found
  nothing"), and `attach_examined_sites(report, root) -> GateReport`
  (a post-`run_gates` enrichment step that populates `examined_sites`
  for every family this module has a reporter for).

- ONE family instrumented for real: `archgate`
  (`frob.gates._arch.arch_examined_sites`), backed by a new
  `ArchResult.files_examined` field (`src/frob/arch/_models.py`)
  populated by `analyze_project` (`src/frob/arch/__init__.py`) from
  `_analyze_one_file`'s own real per-file success/failure return value
  -- NOT from the walk's candidate list. `_analyze_one_file` used to
  return `None` unconditionally; it now returns `bool` (True only when
  it reached a real parse and ran its checks), and every one of its
  five early-return branches (unreadable, no relative-path form, no
  tree-sitter grammar, parse failure) now returns False. This
  distinction is deliberate: reporting a file "examined" that this
  function actually skipped would repeat the exact unsound shape the
  55-waiver incident already proved dangerous, one layer down.

- Enrichment is implemented OUTSIDE `frob.gates.__init__`'s
  `_assemble_gate_report` (a post-`run_gates` step, `attach_examined_
  sites`) rather than threading a new output channel through every
  gate family's own `Callable[[], tuple[Violation, ...]]`/`_ProcessJob`
  dispatch shape there. Two independent reasons: (1) that IS the
  "dozens of independent gate modules" substrate change T-1904's own
  investigation found disproportionate for this ticket's scope, and
  (2) `src/frob/gates/__init__.py` carried a live cross-worktree lease
  (T-1929) for this ticket's entire session, so it could not be
  touched here even if the design called for it. `analyze_project` is
  memoized per `frob check` run (T-0423) -- calling it a second time
  from `arch_examined_sites` inside the same run is a cache hit, not a
  second tree walk.

- `_drop_untrustworthy_mass_stale_candidates`
  (src/frob/gates/_fix_engine_sync.py) is UNCHANGED. No waiver-retirement
  path reads `examined_sites` yet.

ACCEPTANCE PROPERTY, proven directly (tests/unit/gates/
test_examined_sites.py, 10 tests): "it must be impossible for a site
the analysis did not cover to be reported as covered."
`TestSiteExaminedSoundness` covers the four cases the property implies:
an unknown family, a known family with an examined site, a known family
with an UNexamined site, and an instrumented-but-empty family -- the
last three all correctly resolve to False except the genuinely
examined one. `TestAttachExaminedSites.
test_families_this_module_does_not_know_about_stay_absent` is the
direct end-to-end check: run `attach_examined_sites` against a real
fixture tree containing a real python file, and assert `perf`/`strata`
(uninstrumented families) report `is_family_instrumented=False` and
`site_examined=False` regardless -- an uninstrumented family can never
look covered just because SOME family in the same run legitimately was.
`test_archgate_examined_sites_exclude_an_unparseable_file` proves the
`_analyze_one_file`-return-value distinction: a binary file with no
tree-sitter grammar is walked but never reported examined.

Fail-then-pass proof (module-existence form, since this is new-code
addition, not a call-site refactor): moved `_coverage_sites.py` aside
and re-ran the test file -- collection failed with `ModuleNotFoundError:
No module named 'frob.gates._coverage_sites'` (a real, non-vacuous
failure, not "collected 0 tests"). Restored the module and re-ran --
all 10 pass.

Verification: `uv run pytest tests/unit/gates/test_examined_sites.py
tests/unit/test_arch.py tests/unit/test_arch_srp.py
tests/test_arch_gate.py` -- 342 passed, 0 failed (confirms
`_analyze_one_file`'s new bool return does not regress any existing
arch/arch-gate behavior). `uv run ruff check`/`ruff format` on every
touched src file clean. `uv run ty check` on every touched src file
clean. `uv run frob check --only test --ticket T-1921`: initially
surfaced one real TEST001 (arch_examined_sites had no bound unit test)
-- fixed by binding `frob:tests` directives to the two
`TestAttachExaminedSites` cases that exercise it through `attach_
examined_sites`; re-ran clean. `uv run frob check --only affect_drift`
(unscoped): initially surfaced AFFECT001 on every new/changed public
symbol (GateStats, ArchResult, analyze_project, arch_examined_sites,
attach_examined_sites/is_family_instrumented/site_examined) -- resolved
by adding `frob:describes` edges and prose to docs/modules/gates.md's
Data models section, docs/modules/arch.md's Public API section
(`ArchResult.files_examined`), and docs/commands/check.md's Run-scoped
memoization section (analyze_project's memoization contract is
unaffected by the new field); re-ran clean for every one of this
ticket's touched files.

GATE FAMILIES INSTRUMENTED (explicit statement, per the brief's
requirement): `archgate` only. Every other family in `frob.gates.
__init__`'s ~40-entry job registry (strata/sys, perf, graph/clones,
vet-adjacent secrets/taint/opaque, doc/coverage/policy/tickets/etc.) is
NOT instrumented -- `GateStats.examined_sites` carries no key for any of
them, and `is_family_instrumented`/`site_examined` both correctly
report False for all of them, verified directly by this ticket's own
regression test.

RESIDUE (disclosed, filed as draft tickets, will renumber at land):
1. T-1943 -- extend `examined_sites` to the other families
   the 55-waiver incident actually hit (strata, perf, graph, vet) --
   each needs its own reporter function in the shape `arch_examined_
   sites` establishes, added one at a time to `_coverage_sites.
   _FAMILY_REPORTERS`.
2. T-1942 -- wire a THIRD, additive per-site check into
   `_drop_untrustworthy_mass_stale_candidates` once (1) has enough
   family coverage to be useful -- explicitly NOT this ticket's scope,
   per the coordinator's brief and this repo's own standing hardening
   after the original incident.

### Changed
```
 docs/commands/check.md                  |  10 ++
 docs/modules/arch.md                    |  18 ++++
 docs/modules/gates.md                   |  25 ++++-
 src/frob/arch/__init__.py               |  42 ++++++--
 src/frob/arch/_models.py                |  16 +++
 src/frob/gates/_arch.py                 |  33 +++++-
 src/frob/gates/_coverage_sites.py       | 175 ++++++++++++++++++++++++++++++++
 src/frob/gates/_models.py               |  32 +++++-
 tests/unit/gates/test_examined_sites.py | 145 ++++++++++++++++++++++++++
 tickets/T-1921/ticket.md                |  97 +++++++++++++++++-
 tickets/T-1942/ticket.md      |  52 ++++++++++
 tickets/T-1943/ticket.md      |  44 ++++++++
 12 files changed, 677 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_uninstrumented_family_reports_not_examined` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_family_reports_true_for_a_known_site` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_family_reports_false_for_an_unexamined_site` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestSiteExaminedSoundness::test_instrumented_but_empty_family_still_reports_false_for_any_site` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestIsFamilyInstrumented::test_absent_family_is_not_instrumented` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestIsFamilyInstrumented::test_present_empty_family_is_instrumented` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_archgate_examined_sites_include_a_real_python_file` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_archgate_examined_sites_exclude_an_unparseable_file` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_preserves_examined_sites_a_prior_caller_already_attached` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 12 error(s), 2049 warning(s), 696 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, COV003@tickets/T-1872, COV003@tickets/T-1895, COV003@tickets/T-1896, COV003@tickets/T-1900, COV003@tickets/T-1906, DOC001@docs/design/cli-hygiene.md, PRE001@tickets/T-1921, SEC110@src/frob/app/ticket_runner/_new.py, SELFAUDIT001@design, WIRE001@src/frob/gates/_arch.py, WIRE001@src/frob/gates/_coverage_sites.py
