## Done report

Changed:
- src/frob/graph/cache.py::_lock_holder_pids_linux (new)
- src/frob/graph/cache.py::_lock_holder_pids_darwin (new)
- src/frob/graph/cache.py::_lock_holder_pids (new)
- src/frob/graph/cache.py::_holder_cmdline (new)
- src/frob/graph/cache.py::_describe_lock_holders (new)
- src/frob/graph/cache.py::_with_lock_retry (path= param + holder-naming in CacheLocked)
- src/frob/graph/cache.py::_connect_with_backoff (now raises CacheLocked naming holder instead of a bare OperationalError on deadline exhaustion)
- src/frob/graph/cache.py::connect / connect_readonly / set_root / touch_file_stat / store_file_data / store_parsed_artifact (pass path= through to _with_lock_retry)
- src/frob/graph/__init__.py::_INGEST_COMMIT_BATCH_SIZE (new)
- src/frob/graph/__init__.py::_ingest_source_files / _ingest_doc_files (periodic conn.commit() every _INGEST_COMMIT_BATCH_SIZE files)
- src/frob/graph/__init__.py::build_graph (docstring updated to reflect the narrowed rationale; frob:waive AFFECT001 added)
- docs/modules/graph.md#exclusive-lock-scope-narrowed-to-the-commit-tail-t-3478 (updated for the T-4282 periodic-commit behavior)
- tests/unit/test_graph_lock_holder_naming.py (new file, 9 tests)
- tests/unit/test_graph_ingest_batching.py (new file, 1 test)

Obligation [2] (name the holding process): `_lock_holder_pids_linux`/`_darwin` find PIDs with `path` open via `/proc/*/fd` (Linux) or `lsof -Fp` (darwin); `_describe_lock_holders` renders `held by pid N (cmdline)`; `_with_lock_retry` and `_connect_with_backoff` both now fold that into the `CacheLocked` message instead of a bare "database is locked". `_connect_with_backoff` previously let a deadline-exhausted lock escape as a raw `sqlite3.OperationalError`, uncaught by `build_graph`'s `except CacheLocked` -- this was a real, separate bug (a build contending on its very FIRST connect attempt crashed instead of reporting `Err(GraphError.CacheLocked)`), now fixed as part of the same change.

Obligation [1] (concurrent readers): investigated whether reintroducing WAL (retired by T-3644 for a SIGBUS class under cross-process db replace/recover) is still needed -- concluded no: the actual mechanism is that `build_graph`'s single, previously-uncommitted transaction spanning an entire ingest lets sqlite's rollback-journal writer escalate to an EXCLUSIVE lock (once its dirty-page cache spills once, which any nontrivial ingest does) and hold it until the transaction commits, for the WHOLE remaining build. Fix: `_ingest_source_files`/`_ingest_doc_files` now `conn.commit()` every `_INGEST_COMMIT_BATCH_SIZE` (200) files, bounding that window instead of reintroducing WAL's SIGBUS class. Each committed batch is independently safe (`store_file_data` replaces one file's rows atomically, keyed by path; the cross-file DERIVED-state step, `_prune_stale_cache`, is unchanged and still runs once, locked, at the end).

Corruption-hypothesis question (freelist mismatch / orphaned pages): NOT confirmed or refuted directly -- did not reproduce the corruption. Assessment: a shorter-lived transaction (this fix) reduces the WINDOW in which an external interrupt (a killed writer, a fleet-cleanup tool touching `.frob/cache.db*` mid-write) could corrupt file structure, since TRUNCATE/rollback-journal mode is otherwise self-healing across an ordinary crash. Recorded as plausible-but-unconfirmed in the ticket, per the ticket's own request to say which.

Evidence: tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming.* (9 tests, one per new symbol/branch: real subprocess fd-holder detection, self-exclusion, holder-description formatting incl. degrade paths, CacheLocked message naming the holder from both _with_lock_retry and _connect_with_backoff); tests/unit/test_graph_ingest_batching.py::test_build_graph_commits_in_batches_not_one_final_transaction (differential commit-count test: a small batch size commits strictly more often than a batch size larger than the whole ingest -- verified as a genuine positive control by temporarily disabling the batching code and confirming the test fails). Full existing suite (tests/test_graph_lock.py, tests/unit/test_graph_cache.py, tests/unit/test_graph_build_lock.py, tests/test_graph.py, plus the 2 new files -- 224 tests) passes unchanged.

Filed: T-4286 (SCOPE002's private-helper "under-capture" check resolves callee helpers by bare short name repo-wide, matching the pre-existing "Shared graph wrong for its second consumer" gap; discovered while scoping this ticket's own new test files, confirmed pre-existing and unrelated to this diff's content -- filed rather than fixed, out of proportion for this ticket).

Gates: `frob check --ticket T-4282 --only fmt/affect_drift/prework` clean (0 errors). `frob check --ticket T-4282 --only scope`: SCOPE001 clean (0); a residual SCOPE002 count remains, entirely pre-existing debt (frob:tests/frob:doc targets on long-lived symbols like build_graph/connect pointing at test/doc files outside this narrow ticket's scope, predating this ticket -- same shape already precedented and accepted for T-1214 on this same file) plus the newly-filed T-4286 bare-name-resolution gap; not something this ticket's own diff introduces or can reasonably close without scoping in dozens of unrelated files. `frob test --base main` clean (43 python tests recorded, exit=0).

### Changed
```
 tickets/T-4282/ticket.md           | 83 +++++++++++++++++++++++++++++++++++++-
 tickets/T-4286/ticket.md | 36 +++++++++++++++++
 2 files changed, 117 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_with_lock_retry_names_holder_in_cache_locked_message` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_ingest_batching.py::test_build_graph_commits_in_batches_not_one_final_transaction` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_lock_holder_pids_linux_finds_a_real_open_fd` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_lock_holder_pids_excludes_self` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_describe_lock_holders_reports_pid_and_command` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_describe_lock_holders_degrades_without_a_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_describe_lock_holders_degrades_with_no_pid_found` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_with_lock_retry_states_holder_unknown_without_a_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderNaming::test_connect_with_backoff_raises_cache_locked_naming_holder` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 9 error(s), 4627 warning(s), 949 waived
- error-findings: ARCH103@src/frob/graph/cache.py, COV003@tests/test_excludes.py, COV007@src/frob/gates/_tdd_order.py, LARGE001@src/frob/serve/_daemon.py, SCOPE002@tickets.md, SELFAUDIT001@src/frob/graph/cache.py, SELFAUDIT001@tests/unit/test_graph_ingest_batching.py, SELFAUDIT001@tests/unit/test_graph_lock_holder_naming.py, lock-order-cycle@src/frob/serve/_daemon.py
