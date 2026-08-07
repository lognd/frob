---
id: T-1464
title: 'perf: persist parse-artifact cache across process-pool gate workers (correctly
  scoped)'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/__init__.py
- src/frob/graph/cache.py
- src/frob/perf/**
- src/frob/dup/**
- src/frob/gates/_dead_symbols.py
- src/frob/gates/__init__.py
- src/frob/arch/__init__.py
- design/frob.strata
- docs/modules/graph.md
- tests/test_graph.py
- tests/test_graph_lock.py
- tests/unit/test_graph_cache.py
- tests/unit/test_lang_artifact_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/arch/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/arch/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 capability declarations needed for the new lang.os.environ
    read and 2 new test symbols this ticket's fix introduces
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/graph.md
  reason: 'AFFECT001: store_parsed_artifact/load_parsed_artifact/parse_file''s affects()-closure
    doc lives here; documenting the new persistent parse-artifact cache mechanism'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_graph.py
  reason: 'SCOPE002: store_file_data (same file, cache.py, already in scope) has existing
    frob:tests edges into these files'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_graph_lock.py
  reason: 'SCOPE002: store_file_data (same file, cache.py, already in scope) has existing
    frob:tests edges into these files'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: 'COV002: new test files this ticket authored need scope coverage, not per-method
    frob:ticket directives'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_lang_artifact_cache.py
  reason: 'COV002: new test files this ticket authored need scope coverage, not per-method
    frob:ticket directives'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_then_load_round_trips
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_load_miss_returns_none
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_different_fingerprint_is_a_separate_key
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_overwrites_existing_payload
- tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_no_env_is_a_transparent_passthrough
- tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_miss_populates_cache
- tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_hit_skips_extract
- tests/unit/test_lang_artifact_cache.py::TestArtifactCacheLockDegradesGracefully::test_load_locked_is_treated_as_a_miss
- tests/unit/test_lang_artifact_cache.py::TestArtifactCacheLockDegradesGracefully::test_store_locked_does_not_raise
designated_repro_test: null
threat: null
component: null
---
T-1217 investigated but could not be implemented as scoped
(scope=['src/frob/gates/__init__.py', 'src/frob/check/__init__.py']) --
see T-1217's Done report / fail reason for the full investigation.

Root cause confirmed: frob.lang's parse cache (_parse_cache,
src/frob/lang/__init__.py) is a plain in-process dict, cleared per
process -- fine for the single-process thread-pool stages
frob.check._memo.run_memo_scope already covers, but every
ProcessPoolExecutor worker _run_process_gate (gates/__init__.py:6165)
spawns is a FRESH process with an empty cache, so each CPU-bound gate
that calls frob.lang.parse_file/iter_identifiers -- perf (src/frob/perf/**),
clones/dup (src/frob/dup/**), arch (src/frob/arch/**),
dead_symbols (src/frob/gates/_dead_symbols.py), plus sys/pii's own
callers -- independently re-parses and re-extracts the whole repo in its
own worker, no matter how many other gates just did the same work.

The real fix (persist derived per-file artifacts -- body tokens, leaf
identifiers, comment/docstring spans, import specs -- in a sqlite table
keyed by the content hash already in cache.db, and have parse_file/
extract consult that table before re-walking) requires touching:
- src/frob/lang/__init__.py (parse_file/iter_identifiers' own cache
  logic, or a new persistent layer beside _parse_cache)
- src/frob/graph/cache.py (the content-hash-keyed sqlite table itself,
  alongside the existing files/symbols/edges tables)
- every CPU-bound gate module that currently calls parse_file/
  iter_identifiers directly and would need to read the new table
  instead: src/frob/perf/**, src/frob/dup/**, src/frob/arch/**,
  src/frob/gates/_dead_symbols.py (sys/pii's exact call sites need the
  same audit)

None of these are in gates/__init__.py or check/__init__.py -- T-1217's
declared scope structurally cannot reach the actual fix. Re-file with a
scope that includes frob.lang, frob.graph.cache, and the CPU-bound gate
modules above (or split into a foundation ticket for the persistent
cache layer plus one follow-up per consuming gate family, to keep any
single ticket's blast radius reviewable).