---
id: T-0414
title: 'perf: single shared parse pass + memoized frob.lang parse cache (kills 2-6x
  redundant re-parsing; ~90s+ win)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/lang/
- src/frob/check/
- src/frob/graph/
- src/frob/arch/
- src/frob/strata/
- src/frob/vet/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestParseCache::test_cross_entry_point_reuse_is_one_parse_per_file
- tests/test_lang.py::TestParseCache::test_content_change_forces_a_reparse
designated_repro_test: null
threat: null
component: null
---
docs/audits/perf.md H1/H2/H4. frob.lang._parse is UNCACHED, so each source file is tree-sitter re-parsed 2x (arch), 3-6x (vet/selfconform); build_graph has a sqlite parse cache shared with NOTHING; the 745k-node tree is re-walked ~7x/run. FIX: parse every file ONCE per frob check and fan the trees + one walk out to graph/arch/sys/vet/secrets/dup, OR memoize frob.lang._parse content-hash-keyed. sys must reuse the graph snapshot instead of re-parsing imports (H2 ~77s). Add a counter test asserting each file is parsed at most once per invocation. Substrate for the warm daemon T-0177.