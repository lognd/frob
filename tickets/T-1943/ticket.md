---
id: T-1943
title: Extend per-site examined-sites coverage to strata/perf/graph/vet gate families
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
