## Done report

Changed:
- src/frob/strata/_native_staleness.py::_BUILD_ATTEMPT_STAMP_REL, _build_attempt_path, _load_build_attempts, _save_build_attempts (new, private)
- src/frob/strata/_native_staleness.py::record_native_build_attempt (new, public)
- src/frob/strata/_native_staleness.py::stale_natives (body: content-digest branch now checks the build-attempt record before latching)
- src/frob/natives/_build.py::build_natives (body: calls record_native_build_attempt after each crate build that exits zero, never on failure)
- design/frob.strata (new flow f_natives_stratamod: natives -> stratamod)
- docs/modules/cli.md, docs/modules/testing.md (T-2805 sections + new frob:describes anchors)
- tests/unit/strata/test_native_staleness.py, tests/unit/test_natives_build.py (new tests, see evidence)

Root cause, confirmed exactly as measured in the ticket: `maturin --release` on unchanged source is a reproducible build, so the T-0513 content-digest branch's own exit condition (only refresh the stamp once the artifact's BYTES change) could never be satisfied by a genuine rebuild that happened to reproduce the same output -- "genuinely rebuilt, byte-identical" and "never rebuilt, mtime faked" are indistinguishable from mtime/bytes alone, by construction (that indistinguishability is exactly what T-0513's touch-attack defense also depends on, which is why this could not be fixed by loosening the mtime/digest comparison itself).

Fix shape chosen (first of the ticket's three listed options): a REBUILD ATTESTATION. `record_native_build_attempt` is called by `build_natives` immediately after a crate's `maturin develop` exits zero, and records the CURRENT source-tree content digest against the native's name in a separate, `stale_natives`-read-only file (`.frob/native-build-attempts.json`). `stale_natives`'s content-digest branch, before latching, checks whether that record's digest matches the CURRENT source digest -- if so, a real build genuinely ran against exactly this source and reproducibly produced this artifact, so the stamp is refreshed instead of re-flagging. A bare touch can never populate that record (only `build_natives`'s own successful-build call site writes it), so T-0513's original detection is untouched.

Scope was widened beyond the declared `_native_staleness.py` (with `frob ticket scope --add` + recorded reasons, mirrored to main after a couple of land-contention retries) to:
- src/frob/natives/_build.py -- the only place that can legitimately attest "a real build just happened"; _native_staleness.py alone cannot manufacture that signal without re-introducing the exact touch-vs-rebuild ambiguity T-0513 exists to catch.
- both files' existing test suites.
- design/frob.strata -- the new natives -> stratamod cross-import needs a declared Flow (SYS003).
- docs/modules/cli.md, docs/modules/testing.md -- AFFECT001 named both as needing the behavior change documented in the same change.

End-to-end real-world verification (not just unit tests), done live in this worktree against the ACTUAL strata_core crate:
1. Established a real baseline via `stale_natives`.
2. Edited strata-core/src/lib.rs (comment only) and hand-touched the built .so to a later mtime WITHOUT rebuilding -- reproduced `reason="content-digest"`, confirmed it re-fires on a second observation (genuinely latched, matching the ticket's measured symptom).
3. Ran the real `uv run frob natives build` (both crates "built cleanly", rc=0) -- `stale_natives` immediately returned `()`. This is the exact case that failed before this ticket.
4. Edited the source again and touched the artifact again with NO rebuild -- `stale_natives` still reported `reason="content-digest"`, confirming T-0513's original purpose is intact.
5. Reverted the source edit and ran a real `frob natives build` to leave the checkout clean; confirmed `stale_natives() == ()`.

Positive controls, all four, from the ticket:
- Latched + genuine `frob natives build` (byte-identical) -> CLEARS: test_reproducible_rebuild_clears_the_content_digest_latch (designated repro, confirmed FAILED_AT_PARENT at 0e1bfaefe) + the live repro above.
- touch after real source edit, no rebuild -> STILL FIRES: test_touch_after_edit_without_a_build_attempt_still_latches (new) + test_touch_without_rebuild_is_caught_by_content_digest (pre-existing T-0513 regression test, still green, also reproduced live above).
- real edit + real rebuild, bytes change -> clears as today: test_real_rebuild_after_edit_is_not_a_false_positive (pre-existing, still green, unaffected code path).
- fresh checkout, no stamp file -> first-observation path: exercised by every existing test's own baseline-establishing first call (unchanged code path, not touched by this fix).
- FAILED crate build never attests: test_failed_crate_build_reports_not_ok (extended) + test_successful_build_records_a_native_build_attempt (new, confirms the ok=True path DOES attest).

Dead end from the ticket (target/ pruning) not re-chased; confirmed correct as stated.

Evidence: 6 pytest node ids bound, designated repro = test_reproducible_rebuild_clears_the_content_digest_latch, FAILED_AT_PARENT confirmed against 0e1bfaefe.

Filed: none new.

Gates: `frob check --ticket T-2805` clean of anything new -- fixed E501/AFFECT001/DRIFT001/TEST001/SYS003 findings this ticket's own diff introduced (line length, both docs, frob ack on build_natives, frob:tests directive, the new design/frob.strata flow); remaining diagnostics (CYCLE001, COV001, DOC001/DOC006/DOC011, DRIFT002 on unrelated files, PERF004, REG002, SEC110, the pre-existing check/__init__.py SYS003 pair, TEST001 on _multifile.py, TICK003/004/006, CLAUDE001) are pre-existing repo floor, unrelated to this ticket's scope.

### Changed
```
 design/frob.strata                         |   8 ++
 docs/modules/cli.md                        |  20 ++++
 docs/modules/testing.md                    |  21 ++++
 frob.lock                                  |  20 +++-
 src/frob/natives/_build.py                 |  20 +++-
 src/frob/strata/_native_staleness.py       | 168 ++++++++++++++++++++++++++++-
 tests/unit/strata/test_native_staleness.py | 122 +++++++++++++++++++++
 tests/unit/test_natives_build.py           |  43 ++++++++
 tickets/T-2805/ticket.md                   |  85 ++++++++++++++-
 9 files changed, 502 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_reproducible_rebuild_clears_the_content_digest_latch` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_touch_after_edit_without_a_build_attempt_still_latches` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_real_rebuild_after_edit_is_not_a_false_positive` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_touch_without_rebuild_is_caught_by_content_digest` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_successful_build_records_a_native_build_attempt` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_failed_crate_build_reports_not_ok` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 19 error(s), 1189 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
