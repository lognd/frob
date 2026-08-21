---
id: T-2798
title: size a content-hash cache for sys's ast-based capability scan (currently fully
  uncached, largest single stage)
state: in-progress
kind: feature
origin: human
created: '2026-08-21'
priority: high
parent: T-2790
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_scan.py
- src/frob/vet/_capability_python.py
- tests/unit/test_capability_native.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_capability_native.py
  reason: T-2798 threading-parity regression tests for the candidates-threading fix
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2790's profile found sys_gate (69.78s in the real check, the single
largest of the top four stages) dominated by scan_file_capabilities's
Python-aware resolution (_python_binding_capabilities/_python_local_
wrapper_capabilities/_build_py_alias_table/_resolve_py_expr) -- measured
162.37s of a 290.86s profiled selfaudit run (44%). This path is built on
the stdlib ast module (ast.walk/ast.iter_child_nodes both appear directly
in the profile), a THIRD independent parse mechanism from the
tree-sitter path build_graph/perf/dead_symbols/archgate all use in some
form, and unlike those it has NO cache at all today -- not the disk-
backed content-hash cache (T-0414), not the per-run memo (T-0423),
nothing: path.read_bytes() plus a full ast-based walk runs unconditionally
on every one of sys's ~1200 files, every invocation. Confirmed directly:
no memoize/lru_cache/content-hash-cache reference anywhere in
_capability_scan.py or _capability_python.py.

This is a genuinely whole-program analysis in aggregate (capability flow
crosses files: a wrapper in file A calling an exec-ish sink in file B),
matching T-2782's own framing -- but the PER-FILE local fact (what
capability tokens does this one file's content expose, before any
cross-file resolution) is a pure, deterministic function of file content,
same shape as perf/dead_symbols' extract() output (see the sibling
extract()-cache ticket filed alongside this one). This is a bigger lift
than that one: it needs a new cache built from scratch, on a different
parse technology (ast, not tree-sitter), and this ticket's own first job
is to SIZE it, not build it blind -- confirm the per-file local-fact
computation is actually separable from the cross-file resolution step
before committing to a cache shape.

Hard requirements per T-2790's own constraints:
- A positive control: a planted capability violation (e.g. a new eval-ish
  sink reached through a wrapper) must still fire identically through any
  cached path.
- A real, unbudgeted frob check run on this repo must report an
  IDENTICAL finding count before and after.
- No silent caps on what gets scanned or cached.

See docs/investigations/T-2790-check-stage-profile.md (sys section) for
the full profile this ticket is drawn from.