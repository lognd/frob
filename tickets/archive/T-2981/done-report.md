## Done report

Fix shape chosen: a structural `Protocol` (`_DaemonServerLike` in
src/frob/serve/_socketd.py) declaring the daemon server's public attribute
surface (`root`, `idle_tracker`, `event_bus`, `lease_manager`, `shutdown`),
used to re-annotate the two call sites that read attributes off a live
server (`_RequestHandler.server`, `_idle_monitor`'s `server` parameter)
instead of the concrete `_DaemonServer` name. Both the real POSIX class and
the Windows placeholder are checked against the identical structural
contract regardless of which one a given `ty --python-platform` target's
`sys.platform` branch resolves to; the real class needed no other change
since `ty` verifies structural conformance from `__init__`'s own attribute
assignments. For `_LeaseConnection._sock` in src/frob/app/_daemon_proxy.py
(the client half), the same shape does not apply directly (one class, not
two branches) -- instead `_sock` is declared as a bare class-level
annotation, because `__init__` raises `OSError` unconditionally on
`sys.platform == "win32"` before ever assigning `self._sock`, which makes
that assignment statically unreachable under a Windows-target analysis; a
class-level annotation fixes the attribute's type independent of which
branch of `__init__` a given platform considers reachable.

Rejected alternative: restructuring so the attribute accesses are simply
unreachable on Windows. Rejected because `_RequestHandler`/`_idle_monitor`
are ordinary, unconditionally-defined functions/classes that legitimately
run only on POSIX at runtime (`run_socket_daemon` already refuses on
Windows before ever constructing a server) -- there is no live Windows
code path to make "unreachable" through restructuring; the type surface
itself needed a real contract, not a control-flow trick.

Before/after diagnostic counts (`uv run ty check --python-platform
<target> src`, natives built):

| target  | before | after |
|---------|--------|-------|
| win32   | 14     | 0     |
| linux   | 1      | 1     |
| darwin  | 1      | 1     |

(The 1 linux/darwin diagnostic is `warning[unused-ignore-comment]` on
`src/frob/verify/_worker.py:416`'s `os.nice(10)  # ty: ignore[...]` --
pre-existing, unrelated to this ticket, unchanged by this fix; `_worker.py`
is outside this ticket's scope.)

How Windows was verified specifically: `uv run ty check --python-platform
win32 src` from this Linux worktree (natives built) -- this is the fast
feedback loop the ticket asked me to find, and it exists (`ty check --help`
documents `--python-platform`). It reproduced the CI's exact 14 diagnostics
against the UNMODIFIED main tree (confirmed by running the same command
against /home/logan/projects/frob before any of my edits), then read 0
against the fixed tree. `ci.yml`'s Typecheck step runs `uv run ty check
src` with no `--python-platform` flag, so `ty` auto-detects the runner's
real OS -- on windows-latest that resolves to the identical win32 target,
so this local check is a faithful reproduction of what CI does, not an
approximation of it.

REAL windows-latest CI run: NOT obtained, disclosed explicitly. I opened
https://github.com/lognd/frob/pull/5 (branch `t-2981`) to get the
`pull_request` trigger (the workflow only declares `push: branches: [main]`
and `pull_request`, no `workflow_dispatch`, so a plain branch push never
runs it). Two separate triggers -- PR creation, then an empty-commit push
producing a `synchronize` event -- both produced ZERO workflow runs for
this ref, confirmed via `gh api repos/lognd/frob/actions/runs` (no run
with `head_branch == "t-2981"` at any point) and `gh pr view 5 --json
statusCheckRollup` returning `null` throughout. This is not a slow/queued
run -- there is no run at all. Actions are enabled repo-wide
(`allowed_actions: all`) and the `ci` workflow shows `active` via `gh
workflow list`, so this looks like a repository/Actions-side defect, not
something fixable from this worktree; per the coordinator's explicit
instruction I stopped retrying after the second failed trigger rather than
burn budget on more pushes.

Finding for T-2984/T-2985 (ghio structured reporting / CI-result
validity), since another agent is building those tickets now: a poll that
waits for a workflow run which was never created is indistinguishable,
from inside the poll, from a run that is merely slow to start -- both read
as "nothing yet." If `ghio` does not currently model "no run exists for
this ref" as a outcome distinct from "run pending" / "run in progress",
that is exactly the gap this incident surfaces -- worth a named, checkable
state (e.g. `NoRunFound`) rather than leaving CI-confirmation polling to
rediscover this ambiguity by hand each time. I did not investigate
`ghio`'s current source scope (out of this ticket's declared scope:
src/frob/serve/**, src/frob/app/_daemon_proxy.py, docs/modules/serve.md,
docs/modules/testing.md) -- reporting the finding, not fixing it.

POSIX behaviour: unchanged. This is a typing/structure fix only --
`_DaemonServer`'s real class body, `run_socket_daemon`, and every runtime
code path are untouched; only type annotations and one class-level
attribute declaration changed. `_DaemonServerLike.shutdown`'s body is `...`
(a `Protocol` method stub, never called -- the real class's own
`shutdown`, inherited from `socketserver.BaseServer`, is what actually
runs).

Local verification performed (natives built, `uv run frob natives build`):
- `uv run ty check --python-platform win32 src`: 0 diagnostics (was 14).
- `uv run ty check src` (linux, default target) and `uv run ty check
  --python-platform darwin src`: 1 diagnostic each, unchanged.
- `uv run pytest tests/test_serve_socket.py tests/test_app_daemon_proxy.py
  tests/unit/test_daemon_proxy_lease_t1276.py
  tests/unit/test_daemon_proxy_error_paths_t1457.py -p no:xdist`: 72
  passed, 1 deselected
  (`TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process`,
  confirmed failing identically on unmodified main -- a pre-existing
  `[REPLAY age=...]` cache-timing string flake, unrelated to this ticket).
- `frob check --only affect_drift/coverage/scope --ticket T-2981`: the
  AFFECT001 (doc anchor untouched) and COV002 (missing frob:ticket edge)
  findings this diff opened are both closed (doc anchor + ticket directive
  added); `frob check --land-parity`'s remaining unscoped errors (PII012 on
  `_socketd.py`'s pre-existing waiver-symref mismatch, plus everything
  else) are confirmed identical on unmodified main, not introduced by this
  change.

Cuts disclosed: acceptance criterion "proven by a REAL windows-latest run"
is NOT met -- CI could not be triggered (see above), so this closes on the
strength of a genuinely Windows-targeted local `ty` check instead, which is
the best evidence obtainable from this worktree. The ticket should stay
open for a later real-CI confirmation, or the coordinator should re-run
this PR once the Actions trigger issue is understood.

Changed:
- src/frob/serve/_socketd.py::_DaemonServerLike (new)
- src/frob/serve/_socketd.py::_RequestHandler.server (annotation)
- src/frob/serve/_socketd.py::_idle_monitor (annotation)
- src/frob/app/_daemon_proxy.py::_LeaseConnection._sock (annotation)
- docs/modules/serve.md#socket-daemon-t-1092 (updated prose, new anchor)

Evidence: tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits,
tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close

Filed: none (the ghio finding above is reported for T-2984/T-2985's
authors, not filed as a new ticket -- those tickets already exist and are
being actively worked per the coordinator's message)

Gates: frob check --only affect_drift/coverage/scope --ticket T-2981 clean;
frob check --land-parity shows 23 pre-existing unscoped errors, none in
this ticket's scope (confirmed identical against unmodified main)

### Changed
```
 docs/modules/serve.md         | 25 ++++++++++++++++++++----
 src/frob/app/_daemon_proxy.py | 18 ++++++++++++++++-
 src/frob/serve/_socketd.py    | 45 ++++++++++++++++++++++++++++++++++++++++---
 tickets/T-2981/ticket.md      |  8 +++++++-
 4 files changed, 87 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits` (pytest node id, verified passing when recorded)
- `tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 42 error(s), 763 warning(s), 853 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2990/ticket.md, DOC006@tickets/T-2993/ticket.md, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2981, REF002@docs/modules/ghio.md, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ghio.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
