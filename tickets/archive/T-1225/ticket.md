---
id: T-1225
title: 'perf: PERF01x detectors from hot-graph root causes'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_waive.py
- src/frob/gates/_secrets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-1225''s acceptance criterion explicitly requires "each ships as a distinct

    PERF01x rule id with a registry entry" -- docs/design/registry/check-coverage.yaml

    is the live registry `frob check --only registry`''s REG009 gate resolves

    frob:enforces CHK-GATE-PERF0xx directives against. Widening scope to add

    exactly the 4 new CHK-GATE-PERF010/011/013/014 entries (same shape as the

    existing CHK-GATE-PERF001..007 entries already there), nothing else in

    this file touched.

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'Adding the docs/design/registry/check-coverage.yaml CHK-GATE-PERF010/011/013/014

    entries surfaced REG002 (dangling handled_by): the disposition targets a

    rule id that must also exist in src/frob/gates/_waive.py''s _KNOWN_GATE_RULES

    frozenset literal -- the one hand-maintained registry PERF0xx ids live in

    (that module''s own docstring: PERF001-009 are outside _rule_id_scan''s

    SCANNED_BASES auto-detection and are hand-added here). Widening scope by

    exactly one line-range addition (4 new frozenset string literals, same

    shape/location as the existing PERF001-009 entries) so the two registries

    stay mutually consistent, per T-1225''s own acceptance criterion requiring

    "a registry entry" for each new rule id.

    '
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_secrets.py
  reason: 'branch-history artifact: the COV007 waive deletion in _secrets.py belongs
    to sibling T-1318 (landed a579f23e); declared here so the history scan attributes
    it'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_on_fixed_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_in_test_paths
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted
- tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk::test_does_not_fire_on_shared_index
- tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk::test_does_not_fire_on_two_different_trees
- tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop::test_does_not_fire_on_whole_text_single_pass
- tests/unit/perf/test_hotpath_smells.py::TestHotpathSmellsWiredIntoPerfRules::test_perf_rules_includes_perf010_finding
- tests/unit/perf/test_hotpath_smells.py::TestPerf011SkipsNonFunctionSymbols::test_module_level_constant_produces_no_findings
designated_repro_test: null
acceptance:
- text: GIVEN the 2026-07-29 hot-graph report identified 4 recurring anti-patterns
    (yaml.safe_load/yaml.load without the C loader in non-test code; a repo-scan API
    such as xref/exports_consumers/iter_files called inside a loop over symbols; more
    than one ast.walk over the same tree within one function family; a re.finditer
    pattern-list loop nested inside a per-line loop) WHEN each ships as a distinct
    PERF01x rule id with a registry entry and a .strata obligation layer THEN each
    rule fires on the exact pre-fix code shape it was mined from, backed by a regression
    corpus fixture reproducing that shape (e.g. the pre-fix tickets/_store.py, gates/_debt_deprecated.py,
    gates/_pii_structural/__init__.py, and gates/_secrets.py shapes) so a future regression
    re-introducing the pattern is caught statically
  evidence:
  - tests/unit/perf/test_hotpath_smells.py::TestHotpathSmellsWiredIntoPerfRules::test_perf_rules_includes_perf010_finding
threat: null
component: null
---
Companion detector ticket for EPIC A's fixes (T-1206 CSafeLoader, T-1207 repo-scan-in-loop, T-1209 multi-ast.walk, T-1211 regex-per-line): per repo convention, a perf root cause ships as both a .strata obligation and a PERF0xx lint rule, never as a fix-only patch. Four rules to add: (a) 'yaml.safe_load/yaml.load without C loader in non-test code'; (b) 'repo-scan API (xref/exports_consumers/iter_files) called inside a loop over symbols'; (c) '>1 ast.walk(tree) over the same tree in one function family'; (d) 're.finditer with a pattern-list loop inside a per-line loop'. Each needs a PERF01x id, a registry entry, and a regression-corpus fixture reproducing the exact pre-fix shape mined from the report (tickets/_store.py, gates/_debt_deprecated.py, gates/_pii_structural/__init__.py, gates/_secrets.py) so the rule is proven to fire before the corresponding EPIC A fix lands, and to keep firing as a regression guard after.