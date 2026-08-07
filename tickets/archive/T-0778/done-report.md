## Done report

Changed:
- src/frob/gitio.py::run_argv -- routed through frob.process._guard.guarded_subprocess_run so FROB_DISABLE_EXEC=1 refuses every git spawn (Err(GitError.GitFailed), logged) without ever calling subprocess.run; this is gitio's single spawn seam, so the serve daemon (src/frob/serve/_daemon.py, _warm.py, which already call run_argv/working_diff) and every gitio-based read are covered transitively -- no changes needed there.
- design/frob.strata -- rewrote the 4 stale LINT004 waivers that still cite "T-0200 is the follow-on ticket to build one" (fleet, core, tickets_ledger, vet). T-0200 is done and T-0778 wired gitio.py's own spawns, so each waiver now states the honest remaining gap and points at the new follow-on ticket instead of a since-shipped mechanism. Could not delete these waivers outright (contrary to the ticket's literal instruction) -- see Deviations below.
- tests/test_gitio.py::TestRunArgv.test_kill_switch_refuses_without_spawning -- new test: FROB_DISABLE_EXEC=1 makes run_argv return Err(GitError.GitFailed), never calls the real subprocess.run (spied via monkeypatch), and logs a WARNING containing "exec disabled".

Sweep for other bypassing subprocess call sites (grep subprocess.run/Popen/call/check_output outside src/frob/process/_guard.py and src/frob/gitio.py):
- CONFIRMED WIRED (no action needed): src/frob/serve/_daemon.py, src/frob/serve/_warm.py, src/frob/serve/_tools.py all call frob.gitio.run_argv/working_diff, not subprocess directly -- T-0778's gitio wiring covers them.
- STILL BYPASSING, filed as a follow-up (out of T-0778's scope -- none of these files are in scope=[gitio.py, _guard.py, frob.strata, test_gitio.py]):
  - src/frob/tickets/__init__.py:930 `_repo_files_git` -- direct `git ls-files` subprocess.run, NOT routed through gitio.run_argv. This is the closest remaining gap to the audit's "tickets lease" language.
  - src/frob/tickets/__init__.py:2370 `_run_evidence_command` -- shell=True evidence-command spawn.
  - src/frob/gitlog/__init__.py:230 -- direct `git log` subprocess.run.
  - src/frob/app/ticket_runner.py:863,1159; src/frob/fleet/__init__.py:164,194; src/frob/tickets/clipboard.py (9 sites); src/frob/mutate/__init__.py:260; src/frob/deploy/_vm_runner.py:109,116,134,153; src/frob/scaffold/project.py:509; src/frob/testing/_coverage_wait.py:151.
  Filed as T-0803 ("wire remaining subprocess call sites through the T-0200/T-0778 exec guard...").

Deviations from the ticket's literal plan (disclosed, not hidden):
- The ticket said "DELETE the five stale LINT004 waivers" and, if LINT004 then legitimately re-fires, "the honest fix is wiring that node's spawns through the guard, not re-waiving." I found only 4 waivers with this exact reason text today (checker's was already retired with a real attr flag, and stratamod's net waiver was already dropped by T-0769 -- both before T-0778 started; git history in tickets-archive.md confirms the original 5 were checker/core/stratamod/tickets_ledger/vet). Of the remaining 4 (fleet, core, tickets_ledger, vet), NONE could be honestly deleted: each node's `may "exec"`/`may "net"` capability is attributed to files outside T-0778's scope (fleet/__init__.py's own subprocess.run; core's gitlog/mutate/deploy/scaffold/testing subprocess.run calls, only one of core's many code-glob files being gitio.py; tickets_ledger's git-ls-files/evidence-shell/clipboard.py calls; vet's net_enabled() never being called anywhere). Wiring any of those requires touching files outside scope=[gitio.py, _guard.py, frob.strata, test_gitio.py]. Deleting the waivers and declaring `attr flag=` would have been a false completeness claim -- the exact anti-pattern this repo's T-0150/T-0151 discipline (and this very ticket) exists to prevent. Instead I rewrote each waiver's reason to state the real, current state (mechanism exists and is genuinely wired for the git seam; specific remaining unwired call sites named; pointed at the new follow-on ticket T-0803 instead of the shipped T-0200) -- this satisfies the ticket's actual acceptance criterion ("no LINT004 waiver cites T-0200 as pending") without a false claim. `uv run frob sys audit` confirms selfconform stays clean (0 unwaived findings) after this change.

Evidence: tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning
- `uv run --frozen pytest tests/test_gitio.py tests/test_serve_daemon.py tests/system/test_spawn_budget.py -v` -> 33 passed, 2 xfailed (both pre-existing/unrelated).
- `uv run --frozen pytest tests/test_gitio.py -q` -> 23 passed on its own.
- `uv run --frozen pytest tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning --collect-only -q` confirms the node id resolves.

Filed: T-0803 (wire remaining subprocess call sites through the T-0200/T-0778 exec guard)

Gates: `uv run --frozen frob check --only gates-fast --ticket T-0778` clean (0 errors after `frob ticket sweep T-0778` refreshed PRE001); `--only gates-native --ticket T-0778` clean; `--only gates-security --ticket T-0778` clean; `--only static --ticket T-0778` and `--only lint --ticket T-0778` clean (pre-existing exports/frob-dup noise, all `pass`). `uv run --frozen frob sys audit` -> "sys audit: PROVED (4 waived) -- zero UNWAIVED gaps across every configured view" / "self-conformance PROVED -- zero SYS gaps", the 4 WAIVED LINT004 lines are the rewritten fleet/core/tickets_ledger/vet waivers above, no other node newly reds.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
