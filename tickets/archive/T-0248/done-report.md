## Done report

Changed:
- `src/frob/strata/_native_staleness.py` (new) -- `NATIVE_SOURCE_DIRS`
  (`strata-core`, `frob-core`), `StaleNative`, `stale_natives(root)`,
  `stale_native_warning(root)`, `check_native_staleness_or_exit(root)`.
  Compares the newest mtime under each declared `[[native]]`'s source
  directory against the newest mtime among its built compiled artifact(s),
  reusing `frob.testing._collect._compiled_artifacts` (the T-0333
  discovery precedent) rather than re-implementing "find the .so behind an
  importable native name" a second time. An unbuilt native is deliberately
  NOT reported here -- that is T-0333's `missing_natives` diagnostic, a
  different remedy ("build" vs "rebuild").
- `src/frob/strata/__init__.py` -- exports the five new public symbols.
- `src/frob/tickets/_land.py::_warn_if_native_stale` (new) + one call site
  in `_land_squash_apply`, right after the squash-apply lands on `root`
  and before the final commit: logs `stale_native_warning(root)` at
  WARNING if non-None. Non-blocking by design (matches the ticket's "prints
  a LOUD post-land instruction" framing, not "refuses to land") --
  `make core` is cheap to run manually right after seeing it.
- `Makefile::check` -- runs
  `python -c "...check_native_staleness_or_exit(Path('.'))"` before
  `uv run frob check`, so a stale native fails `make check` loudly instead
  of `frob check`/`frob test` silently running against the old native.

Not done (filed instead, out of T-0248's declared scope --
`src/frob/gates/__init__.py` is not in `scope`): fix (2) from the incident
narrative -- distinguishing SYS004's own message text ("unknown construct,
likely a grammar/native mismatch") -- requires editing `_sys004` in
`src/frob/gates/__init__.py`, which T-0248's scope globs do not cover.
Filed as T-draft-832a63a3 (never refiled) ("wire T-0248 stale-native detection into frob
check's SYS004 gate message").

Evidence: 9 node ids (2 unit test classes) --
`tests/unit/strata/test_native_staleness.py::TestStaleNatives` (5 cases:
grammar-ahead-of-native fixture per the ticket's requested regression,
fresh-native no-op, unbuilt-native no-op, no-matching-source-dir no-op,
NATIVE_SOURCE_DIRS convention) and
`::TestCheckNativeStalenessOrExit` (2 cases: exits 1 + prints when stale,
returns None when not); `tests/test_ticket_land.py::TestWarnIfNativeStale`
(2 cases: real `land()` run logs the WARNING when
`stale_native_warning` is monkeypatched stale, and logs nothing on an
unrelated non-native change).

Not Filed: T-draft-832a63a3 (never refiled) (SYS004 message wiring, out of this ticket's scope).

Gates:
- `uv run ruff check` on all changed/new files: clean.
- `uv run ty check` on all changed/new files: clean.
- `uv run pytest tests/unit/strata/test_native_staleness.py
  tests/test_ticket_land.py -p no:cacheprovider -q`: 45 passed.
- REL001 disclosed: this ticket adds five new public symbols to
  `frob.strata`'s surface (`NATIVE_SOURCE_DIRS`, `StaleNative`,
  `check_native_staleness_or_exit`, `stale_native_warning`,
  `stale_natives`) with no accompanying `CHANGELOG.md` entry or version
  bump -- `CHANGELOG.md` and `pyproject.toml` are not in T-0248's declared
  scope (`src/frob/tickets/**`, `src/frob/strata/**`, `Makefile`,
  `tests/**`, `tickets.md`), so REL001 will fire on the next `frob check`
  until the coordinator's release step covers it.
- `frob check --ticket T-0248` not run standalone as a final gate here per
  dispatch instructions (coordinator stamps coverage/full-check at land);
  targeted pytest + ruff + ty above are the verification for this pass.
