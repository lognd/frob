## Done report

Added `frob.serve._watch` (T-1094, child (a) of T-0321): a background
push-invalidation layer over the existing pull-based warm-state cache
(`frob.serve._warm._repo_dirty_key`/`_warm_state`). `watch_tick(root,
last_key)` re-evaluates the SAME `_repo_dirty_key` signature the pull path
already trusts and, on a change (or the first tick), proactively
invalidates and eagerly rebuilds the warm state -- so a query arriving
after an on-disk edit hits an already-warm cache instead of paying the
rebuild inline. `WatchThread` drives this on a short interval
(`DEFAULT_WATCH_POLL_INTERVAL_S`, 1s) as a daemon thread, wired into
`frob.serve._socketd.run_socket_daemon` alongside the existing idle-
monitor thread, started/stopped in the same lifecycle.

Design disclosure (documented in `_watch.py`'s module docstring and
`docs/modules/serve.md`'s new section): this is a fast POLLER reusing
`_repo_dirty_key` itself, not a kernel inotify/watchdog-library
subscription. Reusing the exact signal the pull path already checks means
a watch tick structurally cannot disagree with what a client's own next
query would have computed -- the correctness proof is definitional, not
merely argued -- and it adds no new dependency and sidesteps the
inotify-under-WSL-bind-mount watch-miss class this repo already
documented once (T-0245). The staleness/correctness contract stays intact
by construction: `_warm_state`'s pull-path recheck against
`_repo_dirty_key` runs unconditionally on every tool call regardless of
whether the watcher already pre-warmed the cache; a missed/delayed tick
only means the query pays the rebuild cost it always paid before this
ticket (a forgone optimization), never a stale answer.

The differential harness the ticket's acceptance [1] asks for
(`TestWatchTick.test_watch_tick_never_disagrees_with_pull_signal`) runs a
randomized edit sequence and asserts `watch_tick`'s own "changed" verdict
always agrees with directly comparing two independent `_repo_dirty_key`
calls bracketing the same edit -- true by construction here, but proven on
the real code path.

`on_change` (a `WatchThread` callback) is `None` on its own in this
ticket; T-1096 (landing next, same worktree/wave) wires it to publish a
`graph-changed` event to subscribed clients. `_watch.py` has no import
dependency on `_events.py` at all, so it stands alone correctly even if
T-1096 were dropped.

### Scope note
This worktree also carries T-1096's changes (same scope glob,
`src/frob/serve/**`, landing next in the same wave) already committed
alongside T-1094's -- `src/frob/serve/_events.py`,
`tests/test_serve_events.py`, and the subscribe-protocol additions to
`_socketd.py` are T-1096's own deliverable, not T-1094's; this Done report
covers only `_watch.py`, `tests/test_serve_watch.py`, the `WatchThread`
wiring into `run_socket_daemon`, and the "FS-watch push invalidation"
doc section.

### Changed
```
 docs/modules/serve.md      | 139 ++++++++++++++++++++
 src/frob/serve/_events.py  | 309 +++++++++++++++++++++++++++++++++++++++++++++
 src/frob/serve/_socketd.py | 153 ++++++++++++++++++----
 src/frob/serve/_watch.py   | 188 +++++++++++++++++++++++++++
 tests/test_serve_events.py | 148 ++++++++++++++++++++++
 tests/test_serve_watch.py  | 123 ++++++++++++++++++
 6 files changed, 1038 insertions(+), 22 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 825 warning(s), 425 waived
- error-findings: ARCH001@src/frob/serve/_events.py, INV006@src/frob/tickets/_new_renumber.py, TEST001@src/frob/serve/_events.py
