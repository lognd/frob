## Done report

Exhaustive classification pass completing T-0202's deferred enumerate-first
instruction. Re-grepped every `_log.debug/info/warning/error(` and real
`print(` call site under `src/frob` not already classified by T-0202
(gates/graph/check/logging/app/check_runner.py were already done).

Real `print(` sites (word-boundary grep to exclude `fingerprint(` false
positives): only 6 exist in the whole tree --
`src/frob/__main__.py` (x2, pre-logging-setup: SIGINT handler and the
stale-install warning printed before `AppConfig`/logging exist),
`src/frob/app/vet_runner.py` and `src/frob/app/bind_runner.py` (early
CLI errors before config load), `src/frob/strata/_native_staleness.py`
(documented pre-step, deliberately bypasses the logger per its own
docstring), and `src/frob/render/_renderer.py` (the render primitive
itself, the one sanctioned bare-print site `frob-arch`'s render-lint gate
already exempts). All 6 are already correct; zero conversions needed.

`_log.*` call sites in `src/frob/app/*_runner.py` (32 files besides
check_runner.py; 5 debug / 155 info / 21 warn / 181 error by grep) are, on
inspection, the CLI's user-facing output/error channel by design -- INFO
carries the JSON/text/listing payload a command exists to produce (e.g.
`frob ticket list`, `frob ticket board`, `frob graph query`), ERROR carries
the user-facing failure message before `sys.exit`. This matches the
established convention T-0202's own Done report already documented for
`check_runner.py` and confirmed as "the established, consistent convention
across every runner already" -- not a mixed style needing correction.
KEEP-INFO / KEEP-ERROR across all 32 files; no changes.

Non-app library dirs (strata, vet, fuzz, dup, tickets, testing, perf, lang,
serve, arch, stats, release, policy, mutate, cve) were read in full
(~1200 sites). All are already correctly leveled per the same convention
T-0202 established for gates/graph: DEBUG for internal/per-item diagnostic
detail (parse probing, cache hits, per-symbol elaboration detail), WARNING
for recoverable/degraded paths (unreadable files, malformed config,
fallback taken), ERROR for genuine validation/build failures, INFO for
one-time meaningful command outcomes -- with exactly one exception found:
`src/frob/vet/_scan.py`'s two per-package progress lines
(`_scan_dependencies` and `_scan_dependencies_parallel`, one `_log.info`
per dependency in the scan loop) are the same per-item-in-a-loop
anti-pattern T-0202 fixed in gates/graph (would flood INFO for lockfiles
with hundreds of entries; the scan-complete summary line at the end of
`scan_tree` is already the correct INFO-level outcome). Demoted both to
DEBUG.

No other misclassifications found across the remaining ~1200 sites.

Classification table (grep counts of `_log.debug/info/warning/error(` +
real `print(` sites, `src/frob` excluding tests; dirs already classified
by T-0202 shown for continuity, not re-touched):

| dir | debug | info | warn | error | print | status |
|---|---|---|---|---|---|---|
| gates | 93 | 37 | 62 | 27 | 0 | classified by T-0202; not re-touched |
| graph | 18 | 9 | 20 | 4 | 0 | classified by T-0202; not re-touched |
| check | 0 | 0 | 1 | 0 | 0 | classified by T-0202; not re-touched |
| logging | 0 | 0 | 0 | 0 | 0 | classified by T-0202; not re-touched |
| app/check_runner.py | 1 | 4 | 2 | 5 | 2 | classified by T-0202; not re-touched |
| app (32 other files) | 5 | 155 | 21 | 181 | 4 | audited fully; KEEP-INFO/KEEP-ERROR (CLI output/error channel by design, same convention as check_runner.py); 0 changes |
| strata | 36 | 66 | 67 | 98 | 1 | audited fully; KEEP (already correctly leveled); 0 changes |
| vet | 24 | 40 | 48 | 4 | 1 | audited fully; 2 sites demoted INFO->DEBUG (`_scan.py` per-package progress) |
| fuzz | 13 | 5 | 14 | 4 | 0 | audited fully; KEEP; 0 changes |
| dup | 14 | 10 | 7 | 2 | 0 | audited fully; KEEP; 0 changes |
| tickets | 20 | 47 | 50 | 55 | 0 | audited fully; KEEP; 0 changes |
| testing | 7 | 21 | 18 | 20 | 2 | audited fully; KEEP (the 2 `print(` matches are `python -c "..."` subprocess argument strings, not real call sites); 0 changes |
| perf | 1 | 7 | 5 | 5 | 0 | audited fully; KEEP; 0 changes |
| lang | 6 | 2 | 3 | 5 | 0 | audited fully; KEEP; 0 changes |
| serve | 0 | 8 | 1 | 7 | 0 | audited fully; KEEP; 0 changes |
| arch | 4 | 0 | 0 | 0 | 0 | audited fully; KEEP; 0 changes |
| stats | 1 | 0 | 1 | 0 | 0 | audited fully; KEEP; 0 changes |
| release | 0 | 1 | 0 | 1 | 0 | audited fully; KEEP; 0 changes |
| policy | 2 | 4 | 6 | 6 | 0 | audited fully; KEEP; 0 changes |
| mutate | 0 | 2 | 0 | 0 | 0 | audited fully; KEEP; 0 changes |
| cve | 1 | 1 | 5 | 0 | 0 | audited fully; KEEP; 0 changes |
| \_\_main\_\_.py / render/\_renderer.py | -- | -- | -- | -- | 3 | audited; KEEP (pre-logging-setup SIGINT/stale-install prints, and the render primitive itself, the one bare-print site render-lint's own gate exempts) |

Net result: 2 sites reclassified (INFO->DEBUG in `src/frob/vet/_scan.py`)
out of the ~1350 remaining sites this pass individually inspected (the
`app/*_runner.py` CLI-output convention and the library-module
debug/warn/error levels elsewhere were already correct, contra the
ticket's implicit assumption that a large uninspected backlog meant a
large misclassification backlog -- T-0202's fix addressed the one place
the reported bug actually lived, and the rest of the codebase already
follows the same discipline).

### Changed
```
 src/frob/vet/_scan.py |   9 +++-
 tickets.md            | 137 +++++++++++++++++++++++++++-----------------------
 2 files changed, 81 insertions(+), 65 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_lockfile_arg` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_unsupp_err` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_detects_capabilities_from_node_modules` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_flags_undeclared_capability` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_surfaces_a_cve_fingerprint_finding` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeMultipleLockfiles::test_scan_tree_scans_every_lockfile` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeTimeout::test_slow_package_returns_within_timeout_not_task_duration` (pytest node id, verified passing when recorded)
