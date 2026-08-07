---
id: T-0279
title: frob:tests directive src/target direction disagrees between fresh dsl parse
  and stale graph cache
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestCacheModule::test_tests_edge_direction_agrees_fresh_parse_vs_cache_roundtrip
- tests/test_graph.py::TestCacheModule::test_schema_version_mismatch_wipes_derived_rows
designated_repro_test: null
threat: null
component: null
---
Found while working T-0259: a fresh frob.graph.dsl.parse_directives call on a frob:tests comment placed above a SOURCE symbol (the _conform.py/_generate.py convention) produces Edge(src=<source symbol>, target=<test id text>). But frob.gates._test_edges groups TESTS edges by edge.target, and _test001_002_one looks up unit_edges.get(record.symref) where record.symref is the SOURCE symbol -- these can never match for a freshly-parsed file. Confirmed empirically: a direct parse_file+parse_directives call on the real, unchanged src/frob/deploy/_generate.py reproduces src=source/target=test (the 'broken' shape), while the live GraphSnapshot's cached edges for that same unchanged file come back reversed (src=test/target=source, the 'working' shape) -- meaning the .frob/cache.db entry for that file predates a src/target semantic change in the current dsl.py/gates code and is silently masking the mismatch by never being invalidated. New frob:tests directives placed above SOURCE symbols (matching every existing precedent in the repo) get spurious TEST001 violations; placing the directive above the TEST method instead with the source symref as target works around it (see T-0259's Done report) but is not documented anywhere as the required convention, and every existing source-side directive in the repo is only 'passing' by cache accident. Fix: either (a) make dsl.py's TESTS-kind edge construction match gates.py's consumption (swap src/target, or attach the comment differently), and force a cache-format bump so all existing cached entries reparse under the corrected semantics, or (b) fix gates.py's lookup to match dsl.py's actual output and same cache-bump concern. Either way this needs a full cache invalidation to reveal how many of the repo's existing frob:tests directives are actually silently non-functional.