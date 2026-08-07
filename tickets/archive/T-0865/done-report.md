## Done report

Changed:
```
src/frob/scaffold/_managed.py::_MAKEFILE_CORE_SHIM
src/frob/scaffold/_managed.py::_LEGACY_CARGO_CACHE_MARKERS
src/frob/scaffold/_managed.py::_has_legacy_core_cache_logic
src/frob/scaffold/_managed.py::_text_block_status
tests/unit/test_scaffold_natives_shim.py (new, 6 tests)
```
Evidence: `uv run pytest tests/unit/test_scaffold_natives_shim.py tests/unit/test_scaffold_managed.py tests/unit/test_natives_build.py -q` -> 33 passed; `uv run frob test --base main` -> [PASS] python exit=0. Both acceptance criteria bound via `frob ticket evidence --accepts`.
Filed: none.
Gates: `frob check --ticket T-0865 --only static/lint/gates-security/gates-fast` clean of anything touching `scaffold/_managed.py` or the new test file (ruff/ty/frob-dup/frob-arch/frob-exports all pass). The only findings on `src/frob/scaffold/_managed.py` are pre-existing COV007/INV006 debt already present on that file at HEAD before this ticket (predates T-0865, unrelated to the shim/drift-check change) -- left as-is, out of scope. `gates-fast`'s repo-wide DRIFT002/COV003/SYS findings are pre-existing debt across unrelated modules (`tickets/__init__.py`, `test_frob_self_model.py`'s `design/frob.strata` edges, `strata_core`/`frob_core` native-import `ty` errors in this natives-less worktree per docs/guides/agent-playbook.md#1) -- none touch scaffold or this ticket's scope. `frob ticket done-report`'s CLI hung under multi-agent tickets.md lock contention (bug T-0887); this Done report was hand-written into tickets.md per the playbook's documented fallback.
