## Done report

Extended `frob.gates._coverage_sites`' per-site examined-sites substrate
from archgate-only to also cover perf/strata/graph/vet -- the four
families T-1904's own investigation named as the ones the 55-waiver
incident actually hit.

Changed:
- src/frob/gates/_coverage_sites.py::_load_family_reporters -- registers
  four new reporters in _FAMILY_REPORTERS ("perf", "strata", "graph",
  "vet"), alongside the existing "archgate" entry.
- src/frob/gates/_coverage_sites.py::_perf_examined_sites (new) -- a
  scannable file (tree_sitter_extensions()) whose frob.lang.parse_file
  call succeeds is examined; matches perf_gate's own
  _perf_gate_candidate_paths/_perf_gate_parse_files honesty bar.
- src/frob/gates/_coverage_sites.py::_strata_examined_sites (new) -- a
  `.strata` file under design/ whose read+parse succeeds
  (_parse_one_design_file) is examined; candidate set matches
  frob.strata.load_design_ids' own _strata_files walk.
- src/frob/gates/_coverage_sites.py::_graph_examined_sites (new) --
  frob.graph.build_graph's own GraphSnapshot.file_hashes keys (a file
  that failed to parse lands in parse_failures instead, never gains a
  file_hashes entry).
- src/frob/gates/_coverage_sites.py::_vet_examined_sites (new) -- a file
  whose language has a registered capability-pattern table
  (frob.vet._capability.language_for) and is readable is examined;
  re-derives readability/language-support rather than trusting
  scan_file_capabilities' own empty-return (which is ALSO the correct
  outcome for a genuinely examined, zero-hit file).
- Module docstring updated (FAMILIES INSTRUMENTED TODAY section) to name
  all five families instead of archgate-only.
- tests/unit/gates/test_examined_sites.py -- fixed the one pre-existing
  assertion this change would otherwise break
  (test_families_this_module_does_not_know_about_stay_absent asserted
  perf/strata were NOT instrumented; now asserts against a
  "totally_unknown_family" instead, preserving the acceptance property
  the test actually protects). Added TestPerfGraphVetExaminedSitesShare
  OneFixtureShape (parametrized over perf/graph/vet -- the three
  families that share one fixture shape, to avoid the DUP001/DUP002
  near-duplicate-test findings three separate classes produced) and
  TestStrataExaminedSites (a distinct fixture shape, real .strata
  syntax).

No production caller wired in this same diff -- T-1921's own precedent
for archgate, and the coordinator's standing instruction against
shipping a coverage substrate and its consumer together in one change
(the exact root cause the T-1579 55-waiver incident traces to). Each new
reporter carries its own `frob:waive WIRE001` (no caller yet) plus a
`frob:waive COV005` (this file's four WIRE001 waivers all key off the
same (kind=waive, target="WIRE001") pair per COV005's own docstring, so
a brand-new independent WIRE001 waiver on a new private symbol reads
identically to a rebind of an existing one even though nothing moved --
confirmed by reading _cov005_file's matching logic directly).

Filed T-2011 (open, feature): wires all four new reporters
into a real, additive WAIVE004 guard, the same shape T-1942 already
shipped for archgate.

Filed T-2012 (open, bug): a PRE-EXISTING SCOPE002
scope-declaration gap discovered while investigating this ticket's own
gate:SCOPE errors -- confirmed pre-existing (not caused by this diff) by
reverting T-1943's scope to its original declared value and reproducing
the same 3 gates.md-target SCOPE002 findings against an untouched tree.
Could not fix directly: docs/modules/gates.md is a giant shared hub doc
(310 scope-closure warnings measured directly) and was also under a live
cross-worktree lease (T-2001) at investigation time; adding
src/frob/gates/_arch.py alone to close the sibling edge cascades into
arch_gate's own full test surface (16 further warnings), disproportionate
to this ticket.

Evidence: 9 pytest node ids (tests/unit/gates/test_examined_sites.py --
the 3 parametrized positive cases, the 2 parametrized negative cases, the
graph-specific negative case, both strata cases, and the repaired
pre-existing assertion). Full file run: 18/18 passed.

Gates: frob check --only gates --ticket T-1943 clean for gate:WIRE/
gate:DUP/gate:COV/gate:PRE/gate:SELFAUDIT after the fixes above --
_vet_examined_sites originally used `path.read_bytes()` to confirm
readability, which was a genuine NEW fs.read capability site and
regressed the gates node's SYS111 capability-via ratchet ceiling
(42 -> 43, measured directly); switched to a metadata-only `is_file()`
check instead (the actual content read already belongs to
scan_file_capabilities' own real caller, not this reporter), which
resolved it without touching design/frob.strata (confirmed disproportionate:
adding it to scope alone pulled 123 further scope-closure warnings).
Two residual gate:SCOPE SCOPE001 findings remain against
tickets/T-draft-*/ticket.md (this worktree's own residue-ticket filings,
auto-committed by `frob ticket new`/`scope`, outside T-1943's own
declared scope by construction) -- not code this ticket owns, expected
to resolve at land/renumber the same way every other worktree's
residue-ticket filing does. Repo-wide floor unchanged: gate:DSL (1,
pre-existing, unrelated to this ticket's files).

### Changed
```
 src/frob/gates/_coverage_sites.py       | 205 ++++++++++++++++++++++++++++++--
 tests/unit/gates/test_examined_sites.py |  99 ++++++++++++++-
 tickets/T-1943/ticket.md                |  83 ++++++++++++-
 tickets/T-2011/ticket.md      |  41 +++++++
 tickets/T-2012/ticket.md      |  69 +++++++++++
 5 files changed, 482 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_a_parseable_python_file_is_examined[perf]` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_a_parseable_python_file_is_examined[graph]` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_a_parseable_python_file_is_examined[vet]` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_an_unsupported_extension_is_not_examined[perf]` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_an_unsupported_extension_is_not_examined[vet]` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_graph_reports_false_for_a_file_never_written` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestStrataExaminedSites::test_a_parseable_strata_file_is_examined` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestStrataExaminedSites::test_an_unparseable_strata_file_is_not_examined` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/coverage-family-series/tests/unit/test_tickets_evidence_only_scope.py
