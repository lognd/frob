---
id: T-1943
title: Extend per-site examined-sites coverage to strata/perf/graph/vet gate families
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
- src/frob/gates/_coverage_sites.py
- tests/unit/gates/test_examined_sites.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_examined_sites.py
  reason: new reporters need their own tests bound in this ticket's own scope, matching
    the existing archgate reporter tests already covered by this file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_arch.py
  reason: attach_examined_sites's own regression tests cite arch_examined_sites as
    their frob:tests target; this ticket's own test-file addition needs that closure
    edge
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/gates/_arch.py
  reason: reverting -- pulls in arch_gate's whole closure (16 warnings), disproportionate
    to this ticket's scope
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_arch.py
  reason: attach_examined_sites's own pre-existing regression tests cite arch_examined_sites
    as their frob:tests target; closing that scope edge
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/gates/_arch.py
  reason: reverting closure cascade experiments -- back to ticket's original declared
    scope
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/unit/gates/test_examined_sites.py
  reason: reverting closure cascade experiments -- back to ticket's original declared
    scope
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/gates/test_examined_sites.py
  reason: new family reporter tests belong beside the existing archgate reporter tests
    in this shared file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: this ticket's own new fs.read call (_vet_examined_sites' path.read_bytes)
    needs the gates node's capability via-list updated and its ratchet ceiling bumped
    in the same diff
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: this ticket's own new fs.read call (_vet_examined_sites' path.read_bytes)
    needs the gates node's capability via-list updated and its ratchet ceiling bumped
    in the same diff
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: design/frob.strata
  reason: reverting -- design/frob.strata is a giant shared hub (123 closure warnings),
    disproportionate; reverting both file edits too
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: reverting -- design/frob.strata is a giant shared hub (123 closure warnings),
    disproportionate; reverting both file edits too
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_a_parseable_python_file_is_examined[perf]
- tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_a_parseable_python_file_is_examined[graph]
- tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_a_parseable_python_file_is_examined[vet]
- tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_an_unsupported_extension_is_not_examined[perf]
- tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_an_unsupported_extension_is_not_examined[vet]
- tests/unit/gates/test_examined_sites.py::TestPerfGraphVetExaminedSitesShareOneFixtureShape::test_graph_reports_false_for_a_file_never_written
- tests/unit/gates/test_examined_sites.py::TestStrataExaminedSites::test_a_parseable_strata_file_is_examined
- tests/unit/gates/test_examined_sites.py::TestStrataExaminedSites::test_an_unparseable_strata_file_is_not_examined
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1921 built the per-site analysis-coverage substrate (GateStats.
examined_sites, frob.gates._coverage_sites) but instrumented exactly
one gate family for real: archgate (frob.gates._arch.arch_examined_sites,
backed by ArchResult.files_examined).

T-1904's own investigation named the families the 55-waiver incident
actually hit: strata, perf, graph, vet. None of those are instrumented
yet -- GateStats.examined_sites carries no key for any of them, so
is_family_instrumented/site_examined both correctly (and honestly)
report False for every site in those families today.

Extend coverage: add one reporter function per family, in the shape
frob.gates._arch.arch_examined_sites already establishes (returns
frozenset[str] of repo-relative paths that family's own implementation
actually examined this run, built from the family's own real
success/failure per-site outcome, never from a walk's candidate list),
and register each in frob.gates._coverage_sites._FAMILY_REPORTERS.

Do not skip the "built from real success/failure, not the candidate
list" requirement for any family -- that is precisely the distinction
that kept this substrate honest for archgate (a file with no
tree-sitter grammar is walked but never reported examined).