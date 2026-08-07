---
id: T-0997
title: 'coverage pipeline: merge subprocess coverage and exclude .j2 templates from
  the module map (34% join fraction)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/testing/**
- src/frob/gates/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_lock_excludes_graph_excluded_modules
designated_repro_test: null
acceptance:
- text: given a fresh make coverage + re-stamp, when frob check runs, then TEST011
    deflation and TEST012 j2-divergence findings are gone and join fraction reflects
    subprocess coverage
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_lock_excludes_graph_excluded_modules
threat: null
component: null
---
The first coordinator coverage stamp (269 modules, 3520 symbols) reported join_fraction=0.34 and TEST011 flags it as deflated: most frob system tests exercise frob via subprocess (uv run frob ...; the T-0884/T-0880-era env-sanitized spawns), and that coverage is never captured or merged, so two-thirds of modules read as uncovered and TEST005 findings are untrustworthy. Fix: wire subprocess coverage capture (COVERAGE_PROCESS_START + coverage sitecustomize hook in the spawned env, or coverage run --parallel-mode + coverage combine in make coverage) so child-process execution lands in coverage.xml; ALSO stop mapping scaffold .j2 template files as coverable modules (TEST012 divergence lists 22 of them -- they are templates, not Python modules; exclude in the coverage config or the load_coverage module map). Acceptance: a fresh make coverage reports join_fraction well above 0.34 with subprocess-heavy system tests contributing, and TEST012 reports no .j2 divergence after a clean re-stamp.