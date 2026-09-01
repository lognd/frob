---
id: T-3653
title: 'refactor split: stale carry-forward import in destination becomes circular
  when its own referenced symbol later moves into the same destination'
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/**
- docs/commands/refactor.md
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: 'SCOPE002: doc/test coverage closure for the src/frob/refactor package this
    fix touches pulls in the package''s existing frob:doc target and frob:tests suite
    file'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/test_refactor.py
  reason: 'SCOPE002: doc/test coverage closure for the src/frob/refactor package this
    fix touches pulls in the package''s existing frob:doc target and frob:tests suite
    file'
  actor: logan
  at: '2026-09-01'
evidence:
- tests/test_refactor.py::TestGapRegressions::test_gap5_stale_dest_import_becomes_circular_when_its_own_symbol_later_moves_in
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3628 (ARCH102 split of src/frob/process/_lock.py, cluster 3). needed_import_ops_for_symbols' T-3650 fix prevents a NEW carry-forward from self-importing a name already resident at the destination, but does not retroactively fix an EXISTING import statement a PRIOR split/move already wrote into the destination file, when the name that OLD import references later moves into that SAME destination file in a later split call. Repro: split _worker_inherits_hold (references _canonical_registry_key, still in _lock.py at that point) into _derived_lock.py first -- this correctly adds 'from frob.process._lock import ..., _canonical_registry_key' at the top of _derived_lock.py. Later, split _canonical_registry_key itself (plus derived_state_lock/derived_state_write_lock/DerivedStateLockUnavailable) into the SAME _derived_lock.py -- the OLD top-of-file import line is never revisited, so _derived_lock.py now both imports _canonical_registry_key from _lock.py AND defines it locally: a genuine ImportError (partially initialized module) at real import time, not caught by verify_no_self_import (the import target module frob.process._lock is not the file's own module frob.process._derived_lock in AST terms, so the self-import check's literal same-module test misses it) -- only caught by the module_import verify check, correctly rolling back. Suggested fix: needed_import_ops_for_symbols (or a new post-move pass) should also scan dest_file's OWN existing top-level imports for any name about to be moved INTO dest_file by this call, and strip/rewrite that stale import line -- the same _dest_file_bound_names computation T-3650 added, applied to dest_file's own imports as well as new carry-forward candidates. Worked around by hand for T-3628: manually removed the single stale name from the existing import line (not the moved code, which still went through frob refactor split) before retrying the split.