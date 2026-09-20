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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/
- src/frob/check/
- src/frob/graph/
- src/frob/arch/
- src/frob/strata/
- src/frob/vet/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_core.py'
  actor: logan
  at: '2026-09-19'
  old_length: 587
  new_length: 1707
evidence:
- tests/test_lang.py::TestParseCache::test_cross_entry_point_reuse_is_one_parse_per_file
- tests/test_lang.py::TestParseCache::test_content_change_forces_a_reparse
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/audits/perf.md H1/H2/H4. frob.lang._parse is UNCACHED, so each source file is tree-sitter re-parsed 2x (arch), 3-6x (vet/selfconform); build_graph has a sqlite parse cache shared with NOTHING; the 745k-node tree is re-walked ~7x/run. FIX: parse every file ONCE per frob check and fan the trees + one walk out to graph/arch/sys/vet/secrets/dup, OR memoize frob.lang._parse content-hash-keyed. sys must reuse the graph snapshot instead of re-parsing imports (H2 ~77s). Add a counter test asserting each file is parsed at most once per invocation. Substrate for the warm daemon T-0177.

T-4718 sweep (condensed from src/frob/vet/_capability_core.py, the
`_span_cache` block, trimmed for DOCARCH002's 12-line cap): the trimmed
block's full original text, kept verbatim below.

#: Process-lifetime memo for `_non_executable_byte_spans`, keyed on
#: `(str(path), sha256(source).hexdigest())` -- the same content-hash-keyed
#: shape as `frob.lang`'s own `_parse_cache` (T-0414), never mtime/size, so
#: a content change always misses and a byte-identical revisit always hits
#: regardless of which caller (gate, path) asks first (T-1210). Before this,
#: `sys`+`opaque` each independently re-walked the SAME file's comment and
#: docstring node trees once per public entry point that touches it
#: (`scan_file_capabilities`, `_scan_file_operations`, `_scan_file_
#: fingerprints`, `_opaque_indirection_findings`, `non_executable_line_
#: numbers` -- five call sites in `_capability.py` alone, each independently
#: recomputing the same spans for the same file within one `frob check`
#: run). Guarded by a lock for the same reason `_parse_cache` is: gate
#: stages run concurrently in a `ThreadPoolExecutor`.