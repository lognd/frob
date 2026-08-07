---
id: T-1204
title: 'perf: hot-graph burn-down (2026-07-29 profile)'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
evidence:
- tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_on_helper_loader_indirection
- tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_on_fixed_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_in_test_paths
- tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
- tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_without_libyaml
- tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_under_active_coverage_tracer
- tests/test_vet.py::TestLockfileParsers::test_parse_pnpm_lock
designated_repro_test: null
threat: null
component: null
---
Umbrella epic for the 2026-07-29 in-process cProfile hot-graph report (scratchpad hotgraph/report.md). 11 children, one per ranked PERF candidate (10 from the report's 'Ranked PERF ticket candidates' section) plus a CLI-startup lazy-import fix. Each child fixes a measured root cause AND ships a PERF01x lint rule per repo convention (perf root causes ship as both a .strata obligation and a PERF0xx detector, never fix-only). See STANDALONE ticket 'perf: PERF01x detectors from hot-graph root causes' for the four new detector rules this epic's children rely on.