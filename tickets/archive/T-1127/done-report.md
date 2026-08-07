## Done report

NOTE: exports_runner.py/stats_runner.py/_tools.py's RPC-DEFINITION changes
(frob_exports/frob_stats functions plus the CLI-side _try_*_via_daemon
helpers) were, by accident, folded into T-1126's land commit -- they were
uncommitted in this same worktree when T-1126 landed, and `frob ticket
land` diffs the worktree's current state against main, not just the
committed branch history. Verified functionally harmless at the time
(frob_exports/frob_stats were not yet wired into _socketd._TOOL_DISPATCH,
so any query() call for them would have hit "unknown_method" and fallen
back in-process, same as any other Unreachable/RemoteError case) -- but
untested, gate-unverified code landed prematurely under the wrong
ticket's commit. This ticket (T-1127) completes and verifies that work
properly: added _socketd._TOOL_DISPATCH entries, differential-parity
tests, gate verification, and docs, all of which were genuinely still
missing.

Per T-1106's own disclosure: outline/map/xref are scheduled for REMOVAL
by T-0802's 2026-10-01 sunset -- built NO RPC for those three, per the
ticket's explicit instruction. Built RPCs for exports/stats only.

frob_stats(root, *, window_days=30): the DEFAULT (non-`--agentic`) `frob
stats --json` mode only -- returns StatsReport.model_dump(mode="json")
verbatim, field-for-field identical since both sides dump the identical
pydantic model. `--agentic` (env-var FROB_STATS_AGENTIC) reads a
completely different AgenticReport shape and stays out of this RPC's
scope; `_try_stats_via_daemon` never calls it for that mode.

frob_exports(root, pkg_dir, *, include_private=False, exclude_modules=
()): the DEFAULT (non-`--consumers`, non-`--write`) `frob exports <path>
--json` mode only -- returns ExportsResult.model_dump(mode="json")
verbatim. Unlike every other proxied RPC (all answer for the whole
`root` the daemon itself was spawned for), `frob exports` answers for
ONE SUBDIRECTORY -- discovered this the hard way: a first attempt passed
`cfg.exports_path` itself as query()'s `root` (the daemon-connection
target), producing package_dir="/abs/path/to/pkg" from the daemon vs.
"pkg" (the literal argv string) in-process -- a real payload mismatch
the differential test caught immediately. Fixed by resolving the ACTUAL
repo root via frob.gitio.repo_root(pkg_dir) for the daemon connection,
and sending pkg_dir itself as a separate, explicit RPC param (verbatim,
so it echoes back identically as package_dir). Disclosed a genuine edge
this shape carries that the other RPCs do not: pkg_dir resolves relative
to the DAEMON PROCESS's own cwd server-side, true for a freshly-spawned
daemon (ensure_daemon's spawn inherits the calling process's cwd) but not
guaranteed for a long-lived daemon queried later from a different cwd --
documented in docs/modules/serve.md, not silently assumed correct.

Wired both into src/frob/serve/_socketd.py's _TOOL_DISPATCH (this file
was added to scope -- required to make the RPCs reachable over the wire
at all; frob.serve/__init__.py was also added to scope to re-export both
alongside every existing frob_* RPC, matching the established pattern).

Added 2 new differential-parity tests to tests/test_app_daemon_proxy.py
(real subprocess-vs-subprocess FROB_NO_DAEMON=1-vs-live-daemon diff, the
established pattern): test_exports_json_daemon_matches_in_process,
test_stats_json_daemon_matches_in_process.

Fixed a directive mis-attachment bug my own edit introduced in
stats_runner.py: inserting `_try_stats_via_daemon` between `run`'s
existing frob:ticket/frob:doc/frob:tests/frob:waive ARCH103 comment
block and `run` itself silently re-attached that whole block onto the
new function -- caught by a fresh ARCH103 error on `run` itself (now
undirected) during gate verification, not silently missed. Moved the
block back onto `run`, gave `_try_stats_via_daemon` its own frob:tests
line.

Ran the full touched-test set foreground: `pytest tests/
test_app_daemon_proxy.py tests/test_serve.py tests/test_serve_socket.py
tests/unit/test_app_runners.py -p no:cacheprovider -q` -- all pass.

Ran `frob check --ticket T-1127` in chunks (static, gates-native, test,
coverage+doclink+docanchor): 0 errors attributable to any touched file.
The 28 COV001/COV003 errors present are pre-existing (gates/
_tracked_files.py COV001, several strata-core/src/parse.rs COV003
evidence-staleness findings from T-1099's landed rust-file split),
unrelated to this ticket's files.

Updated docs/modules/serve.md's "Proxied commands"/"Scope cut" sections
with a new subsection covering both RPCs and the pkg_dir caveat.

### Changed
```
 tickets.md | 11 +++++++++--
 1 file changed, 9 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_exports_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_stats_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 17 error(s), 1002 warning(s), 428 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/stats_runner.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1127, SELFAUDIT001@design
