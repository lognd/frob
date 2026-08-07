---
id: T-0413
title: 'perf META-GAP: PERF gate is blind to cross-stage redundant recomputation (frob
  did not detect its own 168s parse waste)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/perf/
- src/frob/gates/
- docs/modules/perf.md
- tests/test_perf.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/perf.md
  reason: T-0413 requires a frob:doc anchor for the new PERF007 public symbol (COV001)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_perf.py
  reason: T-0413 PERF007 acceptance tests live in tests/test_perf.py (dispatch-declared
    file)
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_perf.py::TestPerf007RedundantComputation::test_two_stages_calling_the_same_uncached_parse_is_flagged
- tests/test_perf.py::TestPerf007RedundantComputation::test_single_shared_call_site_is_not_flagged
- tests/test_perf.py::TestPerf007RedundantComputation::test_cached_definition_suppresses_the_warning
- tests/test_perf.py::TestPerf007RedundantComputation::test_no_config_means_no_perf007_checking
designated_repro_test: null
threat: null
component: null
---
THE META-GAP (per the standing rule: frobs own perf stupidity is a frob detection gap). PERF001-004 are per-FUNCTION lexical smells (sort-in-loop, membership-in-loop, nested-equality). They are structurally blind to the ACTUAL dominant cost: the same expensive input (a source file / the whole repo) parsed+walked N times ACROSS stages -- ~168s of redundant CPU that PERF never flagged. Add an enforcement (PERF005+/architecture-level) that catches "the same expensive computation is repeated on the same input across call sites/stages" and "an uncached hot function is called on the same key many times" -- e.g. detect a parse/hash/walk over the same path invoked from N stages with no shared cache. It should have red-flagged frob.lang._parse being called 2-6x per file. Ships per-project (T-0406). Acceptance: a fixture that parses the same file twice across two stages with no cache is flagged; a single-shared-parse version is not.