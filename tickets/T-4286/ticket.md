---
id: T-4286
title: SCOPE002 private-helper check resolves bare-name test helpers across the whole
  repo, flooding unrelated findings
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_scope*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4282: adding two small, genuinely new test files (tests/unit/test_graph_lock_holder_naming.py, tests/unit/test_graph_ingest_batching.py) to a ticket's scope -- containing no shared-name helper collisions of their own -- triggered ~20-30 SCOPE002 'private-helper call(s) into <file>, not in scope (probable under-capture)' findings pointing at dozens of UNRELATED test files across the repo (e.g. tests/unit/test_wire001_*.py, tests/unit/test_ack_runner.py), none of which the ticket's diff touches or has any relationship to.

Root cause (measured): the finding's own edge text reads like 'src/frob/graph/cache.py::store_file_data -> tests/unit/test_wire001_atexit_register.py::_write' -- cache.py's store_file_data has test coverage via SOME test that calls a locally-defined _write(root, rel, content) helper (a naming convention dozens of test files independently reuse), and the SCOPE002 checker resolves that call by BARE SHORT NAME across the entire repo rather than within the actual caller's own module/file, attributing a dependency on every other file that happens to define a same-named private helper. This is the same blind spot already documented in project lore as 'Shared graph wrong for its second consumer' (callgraph resolving callees by bare short name repo-wide, e.g. 17 files defining _run), now confirmed to also apply to gate:SCOPE's own private-helper under-capture check, not just the general callgraph consumer.

Confirmed pre-existing and NOT caused by any specific diff: reproduced by adding only two newly-authored, dependency-free test files to a ticket's scope on an otherwise-clean ticket; zero such findings appear when scope is source-files-only, and the flood appears regardless of which two files add coverage in tests/unit/test_graph_cache.py's existing (already-shared) test coverage of store_file_data/store_parsed_artifact.

Suggested fix direction: resolve a private-helper call target by the caller's OWN file/module first (exact qualified match) before falling back to a repo-wide bare-name scan, the same fix shape as the general callgraph fix implied by the existing 'second consumer' lore entry -- or, short of a full resolver fix, scope the private-helper SCOPE002 sub-check to same-file/same-package calls only, since a cross-file call to a PRIVATE (underscore-prefixed) helper in an unrelated file was never a real dependency to begin with.