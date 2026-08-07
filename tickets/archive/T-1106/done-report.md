## Done report

Wired one additional query-shaped CLI command through the T-1093 daemon
proxy on top of `frob perf hot --json`: `frob graph affects <ref> --json`.

Scope narrowed per dispatch instructions before starting: `src/frob/app/`
was contended this wave (ticket_runner.py owned by a sibling ticket,
app/ subject to a late arch extraction). Replaced the broad `src/frob/
app/` scope entry with just `src/frob/app/graph_runner.py` -- the file
this command actually needed touched.

src/frob/app/graph_runner.py: `_try_affects_via_daemon(root, cfg)` tries
`frob.app._daemon_proxy.query(root, "frob_affects", params)` (the RPC
method has been exposed by `_socketd._TOOL_DISPATCH` since T-1092, just
never wired to a CLI command); a hit renders
`_affects_payload_from_daemon`'s reshaped dict (one key rename, `ref` ->
`root`, the only reconciliation needed between the RPC's dict and
`_affects_json_payload`'s existing CLI shape -- everything else,
`dependents`/`docs`/`tests`/`truncated`, is identical) and returns with
zero local graph load/resolve/walk. `_run_affects` calls this helper
first; any `Err` (disabled, unreachable, JSON-RPC error) falls straight
through to the exact in-process path unchanged from before this ticket.
Extracted into its own function (not inlined into `_run_affects`) to
keep the CLI entrypoint under ARCH001's line-count threshold; also moved
the pre-existing `frob:waive ARCH103` comment back onto `_run_affects`
after the extraction shuffled it (it had drifted onto a neighboring
function).

tests/test_app_daemon_proxy.py:
TestDifferentialParity.test_graph_affects_json_daemon_matches_in_process
-- the same real subprocess-vs-subprocess (`FROB_NO_DAEMON=1` in-process
vs a live daemon) diff pattern `test_perf_hot_json_daemon_matches_in_
process` already established, applied to `frob graph affects --json`.
Also generalized `_json_tail`'s helper to recognize a bare JSON object
(`{`) as well as an array (`[`), since `frob graph affects --json`
prints a dict, not a list.

docs/modules/serve.md: added the new command to "Proxied commands" and
narrowed "Scope cut (disclosed)" to explain the remaining gap precisely
-- `frob_graph_query`/`frob_check_delta`/`frob_run_touched_tests`/
`frob_doable_tickets` need a CLI-side shape reconciliation only
(T-1128, a coordinator refile after the draft died); `outline`/`map`/
`xref`/`exports`/`stats` need NEW
server-side `_tools` functions first (no RPC method exists for any of
them yet) -- a materially bigger gap than a reconciliation, called out
separately so it isn't mistaken for the same kind of follow-on work.

Cut: `frob ticket doable` again left unwired (ticket_runner.py
contended this wave, as T-1093 already noted for the same reason).

### Changed
```
 docs/modules/serve.md          | 50 ++++++++++++++++++++++++---------
 src/frob/app/graph_runner.py   | 61 +++++++++++++++++++++++++++++++++++++---
 tests/test_app_daemon_proxy.py | 64 ++++++++++++++++++++++++++++++++++++++----
 tickets.md                     |  3 +-
 4 files changed, 152 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_graph_affects_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
