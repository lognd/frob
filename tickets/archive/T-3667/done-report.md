## Done report

Windows CI run 33521416410 (T-3659's campaign): all 10 tests in tests/gates_suite/test_protocol.py fail on win32, every one with the same shape (`protocol_summary_gate` finds ZERO PROTO002/PROTO003/PROTO004 violations across every Python/Rust/TypeScript fixture and rule family). The win32 captured log for the first failure showed the tagged entrypoint under an ABSOLUTE-path symref ('C:/Users/runneradmin/.../src/a.py::enter') inside compute_protocol_summaries's own reachability universe, while _tagged_symbols_by_package's own entrypoints carry the correct repo-relative symref -- two different spellings of the same function mean it is never "reachable from itself", so no summary is ever computed and every rule that reads off result.summaries finds nothing.

Root cause, traced to source (src/frob/gates/_protocol_summary.py::_package_edges): the function reads a file via `parse_file(root / rel_path)`, whose returned `ParsedFile.path` is built by `frob.lang._display_path` -- which returns `path.relative_to(Path.cwd()).as_posix()` when the file happens to live under the CURRENT process's cwd, else `path.as_posix()` (an ABSOLUTE, always-POSIX-normalized path). `parse_directives` builds every `Edge.src`/`origin` from THAT string. `_package_edges` then tried to strip the absolute prefix back off by SEPARATELY recomputing `abs_path = str(root / rel_path)` and calling `e.src.replace(abs_path, rel_path, 1)` -- but `str(root / rel_path)` is NOT guaranteed to equal `ParsedFile.path`: on win32 `str()` renders native `\` separators while `_display_path` always uses `/`, so the `.replace()` call is a silent no-op and every edge keeps its WRONG (absolute, `_display_path`-shaped) `src`/`origin` -- exactly the symptom observed. This is invisible on POSIX only because `str()` and `.as_posix()` happen to coincide there for the common case where `Path.cwd()` is NOT under the test's tmp_path (the fallback `path.as_posix()` branch) -- but the SAME class of bug is fully reproducible on POSIX too whenever `Path.cwd()` genuinely lands under the scanned root, since `_display_path` then takes its OTHER branch (relative-to-cwd, a short string) which `str(root / rel_path)` (long absolute string) never matches either.

Fix: `abs_path = result.danger_ok.path` (i.e. `ParsedFile.path` itself) instead of recomputing a second, potentially-divergent string -- guarantees the `.replace()` always matches, on every platform, regardless of `Path.cwd()`'s relationship to `root`.

Evidence: tests/gates_suite/test_protocol.py::TestProtocolVerificationGate::test_finds_the_violation_even_when_cwd_relativization_diverges -- monkeypatches `Path.cwd` to land under `tmp_path`, forcing `_display_path` down its relative-to-cwd branch (a POSIX-reproducible instance of the general class of bug win32's native-separator instance is one member of), then asserts `protocol_summary_gate` still finds the PROTO002 violation. `--check-repro` against the test-only commit (5654fbb8b) confirms a GENUINE repro (not confirmatory-only) -- this is the one bucket in T-3659's campaign fully verifiable end-to-end on POSIX, no `--designate-repro-force` needed.

Verification: `pytest tests/gates_suite/test_protocol.py` -- 39/39 pass (was 38/39 minus the new test before the fix, now including it). `ruff check` on both touched files: no issues.

This closes T-3659's most-uncertain bucket -- the original ticket body flagged this as needing windows-side instrumentation to pin down; the captured-log evidence quoted there (the absolute-path symref in the T-0745 "not reachable" warning) turned out to be sufficient to trace the exact call site without it.

### Changed
```
 src/frob/gates/_protocol_summary.py | 20 ++++++++++++++-
 tests/gates_suite/test_protocol.py  | 51 +++++++++++++++++++++++++++++++++++++
 tickets/T-3667/ticket.md            |  4 ++-
 3 files changed, 73 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/gates_suite/test_protocol.py::TestProtocolVerificationGate::test_finds_the_violation_even_when_cwd_relativization_diverges` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
