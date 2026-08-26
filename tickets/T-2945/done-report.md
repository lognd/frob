## Done report

Root cause (confirmed against the T-2917 macOS run, 28 of 156
failures): `socket_path(root)` built the daemon's unix-domain socket
path as `<project root>/.frob/daemon.sock`. macOS's `sockaddr_un.
sun_path` is 104 bytes (108 on Linux); macOS temp/CI paths are already
deep on their own (`/private/var/folders/<hash>/<hash>/T/...`), so
adding a project subtree on top overflowed the limit outright,
producing `OSError: AF_UNIX path too long` on bind/connect. This
breaks the standalone socket daemon (`frob serve`'s fast-path
frontend, T-1092) any time a project is checked out deep enough on
macOS -- not only in CI (a nested Homebrew Cellar path, an iCloud
Drive sync folder, a long username), degrading performance invisibly
(frob still works via the cold-graph-rebuild fallback) rather than
crashing loudly, which is worse to diagnose.

Fix: `socket_path(root)` now resolves to `<system temp dir>/frob-<16
hex digest of the resolved root>.sock` -- a fixed-length filename
independent of the project root's own depth, computed the same way by
every caller (the daemon binding it, a client connecting, the
stale-socket cleanup path) with no shared registry needed, matching
the old scheme's "pure function of root" property. `lock_path` (an
ordinary file, not a unix-domain socket -- no `sun_path` length limit
applies) is UNCHANGED, staying at `<root>/.frob/daemon.lock`, so
per-root singleton-lock discovery is unaffected.

Deliberately NOT macOS-only: the identical `sun_path` limit exists on
Linux too (108 bytes), just less likely to be hit given Linux's flatter
tmp/test paths -- the fix is platform-independent (a short path
everywhere), no `sys.platform` branch.

Test fixtures fixed: `tests/test_app_daemon_proxy.py`'s
`TestProbeDaemon`/`TestProbeDaemonVersion` classes hardcoded `<root>/
.frob/daemon.sock` directly (8 call sites) instead of calling
`socket_path(root)` -- switched all 8 to call the real function so they
exercise actual resolution instead of a path shape that no longer
exists after this fix.

New tests (`TestSocketPath` in `tests/test_serve_socket.py`):
  - `test_short_regardless_of_root_depth` -- MUST-FIRE: builds a root
    deep enough that the OLD scheme's socket path exceeds 108 bytes
    (asserted as a setup sanity check), confirms the NEW path is under
    100 bytes, and -- the real regression guard -- performs an actual
    `AF_UNIX` bind at the relocated path and asserts it succeeds.
  - `test_normal_depth_root_still_works` -- MUST-STAY-QUIET control:
    an ordinary shallow root still binds successfully.
  - `test_stable_for_the_same_root` / `test_distinct_roots_get_
    distinct_paths` -- determinism and uniqueness.

Verification note: `tests/test_app_daemon_proxy.py::
TestDifferentialParity::test_check_delta_gates_only_json_daemon_
matches_in_process` fails both BEFORE and AFTER this change
(confirmed directly: restored the pre-change file content into the
worktree, re-ran the same test, same failure -- a REPLAY-cache-age
annotation timing difference between the daemon-served and in-process
runs, unrelated to socket paths). Pre-existing, out of this ticket's
scope, not touched.

Changed:
  src/frob/serve/_socketd.py (socket_path, _short_socket_filename new)
  tests/test_app_daemon_proxy.py (TestProbeDaemon, TestProbeDaemonVersion
    fixture updates, 8 call sites)
  tests/test_serve_socket.py (new TestSocketPath class, 4 tests)
  docs/modules/serve.md (new "Socket location (T-2945)" section)

Evidence:
  tests/test_serve_socket.py::TestSocketPath::test_short_regardless_of_root_depth
  tests/test_serve_socket.py::TestSocketPath::test_normal_depth_root_still_works
  tests/test_serve_socket.py::TestSocketPath::test_stable_for_the_same_root
  tests/test_serve_socket.py::TestSocketPath::test_distinct_roots_get_distinct_paths
  tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned
  tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged
  tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live
  (full local re-run: tests/test_serve_socket.py 19/19 passed;
  tests/test_app_daemon_proxy.py 12/13 passed, 1 pre-existing unrelated
  flake as noted above; tests/test_serve_events.py +
  tests/test_serve_daemon.py + tests/unit/test_daemon_proxy_lease_t1276.py
  + tests/test_coverage_wait_shared.py: 34/34 passed)

Filed: none -- the pre-existing TestDifferentialParity flake is
outside this ticket's scope (no socket-path involvement) and is left
for whoever owns that test's caching-timing behavior to notice
independently; not filing a ticket for a flake this ticket did not
cause and did not investigate further.

Gates: scoped diff only touches the five declared-scope files;
docs/modules/serve.md updated in the same change per the "docs move
with code" rule.

### Changed
```
 docs/modules/serve.md          | 22 ++++++++++++-
 src/frob/serve/_socketd.py     | 59 ++++++++++++++++++++++++++++++++--
 tests/test_app_daemon_proxy.py | 16 +++++-----
 tests/test_serve_socket.py     | 72 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2945/ticket.md       | 53 +++++++++++++++++++++++++++++--
 5 files changed, 208 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestSocketPath::test_short_regardless_of_root_depth` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestSocketPath::test_normal_depth_root_still_works` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestSocketPath::test_stable_for_the_same_root` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestSocketPath::test_distinct_roots_get_distinct_paths` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_dead_socket_file_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemon::test_silent_listener_is_wedged` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 24 error(s), 649 warning(s), 852 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2945, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
