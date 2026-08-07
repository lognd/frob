## Done report

Converted all three of FMT001/REG010/REL002's delegated write sites to
crash-safe primitives, matching T-1348's `_write_text` posture for
`frob.gates._fix_engine`:

- FMT001 (`frob.gates._fmt_directives._write_formatted`): replaced the
  bare `open(path, "w", newline="")` with a local temp-file + fsync +
  `os.replace` primitive. Cannot reuse `frob.tickets._store.atomic_write`
  directly -- it has no `newline=""` opt-out, and losing that would
  silently re-translate a CRLF file's line endings on every `frob fmt`
  run (the exact T-0441 regression the module's own docstring documents).
  A killed process now leaves the original file intact; re-raises the
  original OSError on failure (unchanged failure-visibility contract).

- REG010 (`frob.registry._staleness.sync_gate_rule_entries`): replaced
  the bare `registry_path.write_text` with `frob.tickets._store.
  atomic_write`. On the (should-never-happen) write-failure path, this
  returns `Err(CorpusError.FileNotFound)` -- not a semantically precise
  fit, but a deliberate reuse of an existing `CorpusError` member rather
  than widening the function's public error type: the two other call
  sites (`frob.app.registry_runner._run_sync_gate_rules`,
  `frob.app.ticket_runner._land_cmd`) key a message dict on `CorpusError`
  alone and sit outside this ticket's declared scope. Filed
  T-1533 to give write failures a dedicated `CorpusError`
  member with the two call sites' scope included.

- REL002 (`frob.release`): added `_atomic_write_release`, a thin wrapper
  around `atomic_write` that translates `TicketError` into a new
  `ReleaseError.WriteFailed` member, and routed all four of the module's
  write sites through it: `stamp`, `rewrite_pyproject_version`,
  `changelog_skeleton_entry`, `set_manifest_version` (the last two were
  not named in the ticket body's bullet list but live in the same
  `src/frob/release/**` scope and had the identical bare-`write_text`
  hazard, so they got the same fix in the same pass rather than leaving
  a known-identical gap next to a closed one).

Changed:
  src/frob/gates/_fmt_directives.py::_write_formatted
  src/frob/registry/_staleness.py::sync_gate_rule_entries
  src/frob/release/__init__.py::_atomic_write_release (new)
  src/frob/release/__init__.py::stamp
  src/frob/release/__init__.py::rewrite_pyproject_version
  src/frob/release/__init__.py::changelog_skeleton_entry
  src/frob/release/__init__.py::set_manifest_version
  src/frob/release/__init__.py::ReleaseError.WriteFailed (new member)

Evidence: 7 new unit tests, each simulating an `os.replace` failure
mid-write and asserting the original file survives byte-for-byte with
no leftover temp file -- see the evidence list below.

Filed: T-1533 (CorpusError needs a dedicated write-failure
member; out-of-scope companion fix for REG010's error-mapping
compromise above).

Gates: `frob check --only test --ticket T-1359` and `frob check --only
coverage --only scope --only prework --only fmt --ticket T-1359` both
0 errors (measured after adding the ticket's own test files to scope
via `frob ticket scope T-1359 --add`, wrapping two new frob:tests
directive lines to canonical form via hand-applied backslash
continuation matching `frob fmt`'s own canonical shape, and re-running
`frob ticket sweep T-1359`). `frob check --only archgate --ticket
T-1359` also 0 errors. Full pytest run of the three touched test files:
81 passed (`tests/test_gates_fmt_directives.py`,
`tests/test_registry_staleness.py`, `tests/test_release.py`).

### Changed
```
 design/frob.strata                            |  16 +-
 docs/design/registry/EXHAUSTIVENESS-GATE.md   |   7 +
 docs/modules/release.md                       |  37 +-
 src/frob/app/ticket_runner/_land_cmd.py       |  26 +-
 src/frob/gates/_fmt_directives.py             |  34 +-
 src/frob/registry/_staleness.py               |  30 +-
 src/frob/release/__init__.py                  |  69 +++-
 tests/test_gates_fmt_directives.py            |  42 +++
 tests/test_registry_staleness.py              |  32 ++
 tests/test_release.py                         |  97 +++++
 tests/test_ticket_land.py                     | 222 ++++++++++++
 tests/unit/test_ticket_runner_land_release.py |  46 ++-
 tickets.md                                    | 492 +++++++++++++++++++++++++-
 13 files changed, 1107 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestWriteFormattedCrashSafety::test_leaves_original_on_replace_failure` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestWriteFormattedCrashSafety::test_preserves_crlf_newline` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestSyncGateRuleEntriesCrashSafety::test_leaves_original_on_replace_failure` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestCrashSafeReleaseWrites::test_stamp_leaves_original_manifest_on_replace_failure` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestCrashSafeReleaseWrites::test_rewrite_pyproject_version_leaves_original_on_replace_failure` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestCrashSafeReleaseWrites::test_changelog_skeleton_entry_leaves_original_on_replace_failure` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestCrashSafeReleaseWrites::test_set_manifest_version_leaves_original_on_replace_failure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
