## Done report

Investigated T-1128's disclosed residual (frob_check_delta's CLI/RPC
payload-shape gap) and implemented the second of its two named candidate
directions -- not the first (running the entire non-gate tool pipeline
inside the RPC, still judged too large; ruff/ty/arch/cycle/dup/bind/
exports never touch the daemon's warm graph/baseline cache the way gates
does, so folding them in would be a second copy of check_runner.py's own
dispatch logic server-side for no real correctness gain).

Widened `frob_check_delta` (src/frob/serve/_tools.py): now also returns a
`check_result` key -- the SAME per-gate-family `ToolResult` list
`frob.check._python._gates_success_result` builds for `frob check --only
gates --delta --json`'s CLI path, wrapped as `{"path": ..., "results":
[...]}` (a CheckResult-shaped dict). Reuses the existing rendering code
directly rather than hand-building a second summary; the pre-existing
flat `delta`/`violation_count`/`baseline_stale`/`ticket` keys are
UNCHANGED (kept for any narrower existing caller of this RPC).

Wired the daemon proxy CLI-side (src/frob/app/check_runner.py,
`_try_check_delta_via_daemon`): fires ONLY for the one narrow shape --
`--only gates` exactly (no other tool stage or individual gate id mixed
in), `--delta` set, a single detected project language (python only, no
polyglot SKIPPED-line siblings), and no `deploy/` stage to append. Falls
through to the in-process path for everything else (a plain `frob check
--json` full multi-tool run, a mixed `--only`, no `--delta`, a
polyglot/deploy project, or an older daemon whose RPC has not been
widened yet -- detected by the `check_result` key's absence). Same
contract every other `_try_*_via_daemon` function in this codebase
follows (T-1106/T-1128).

Key finding, disclosed: true byte-for-byte parity of the FULL
`gate-summary` `ToolResult` is not achievable -- its `summary` field
carries a real per-gate wall/cpu timing blob that legitimately differs
between two independent process runs (one warm-cache via the daemon, one
cold in-process). The new differential-parity test
(tests/test_app_daemon_proxy.py::TestDifferentialParity::
test_check_delta_gates_only_json_daemon_matches_in_process) normalizes
just that one timing segment before comparing (a documented, narrow
exception, not a general relaxation) -- every other field (every
violation, diagnostic, per-family ToolResult, and the summary's own
error/warning/waived counts) is still asserted byte-for-byte, and the
run's exit code is asserted to match too.

Added a plain unit test (tests/test_serve.py::TestCheckDelta::
test_check_result_matches_only_gates_delta_cli_shape) asserting the
`check_result` shape without spawning the real daemon, alongside the
subprocess-vs-subprocess differential-parity test above.

Scope: widened from the ticket's initial declaration to add
tests/test_serve.py and tests/test_app_daemon_proxy.py (`frob ticket
scope --add`, reasoned) once the payload-shape change needed coverage in
both.

Updated docs/modules/serve.md: `frob_check_delta`'s own bullet now
documents `check_result`; a new "Proxied commands" bullet documents the
`--only gates --delta --json` proxy case and its timing-normalization
caveat; the "Scope cut (disclosed)" prose is updated to describe what
T-1147 actually resolved (the narrow proxy case) vs. what stays
genuinely out of scope (the full multi-tool `--json` shape, still not
proxied by any invocation this change wires).

Verification:
- `uv run ruff check src/frob/serve/_tools.py src/frob/app/check_runner.py
  tests/test_app_daemon_proxy.py tests/test_serve.py` -- all clean.
- `uv run pytest tests/test_serve.py tests/test_app_daemon_proxy.py
  tests/unit/test_app_runners_batch6.py tests/system/test_cli_check.py -p
  no:cacheprovider -q` -- exit 0, all pass (dot summary, no F).
- `uv run frob check --ticket T-1147 --only coverage --only drift --only
  invariant --only prework --only registry` -- DRIFT clean (the RPC's own
  wired-test directive resolves once the unit test above existed); COV
  (24) and INV (2) are pre-existing, unrelated debt (verified none
  reference _tools.py/check_runner.py/the two test files this ticket
  touched); PRE001 cleared by `frob ticket sweep T-1147`.

Filed: none. The FULL multi-tool `frob check --json` proxy (no `--only
gates`) remains a disclosed scope cut in docs/modules/serve.md, same as
before this ticket -- no new follow-up ticket needed since the doc
already tracks it as an open, deliberate non-goal rather than a gap to
requeue.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_serve.py::TestCheckDelta::test_check_result_matches_only_gates_delta_cli_shape` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestCheckDelta::test_delta_against_fresh_baseline_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
