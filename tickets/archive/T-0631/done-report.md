## Done report

Implements both T-0577 deferred items.

(1) TICK005-backed regression sweep at land time: `_tick005_land_regressions`
(src/frob/tickets/_land.py) mirrors gates.py's TICK005 (T-0537) terminal-
state-regression semantics -- any ticket DONE/DROPPED in root's pre-land
ledger that is neither terminal nor archived in the post-splice ledger --
but runs it directly around `_squash_and_splice_ledger`'s own splice
instead of depending on a real two-parent merge commit, since a
squash-apply land only ever produces a single-parent commit and the
gate's own HEAD^2 precondition can never fire for a land at all. On a
detected regression, `land()` unwinds the staged squash via
`_verified_reset_root` and returns the new `LandError.TerminalStateRegression`
variant instead of committing. Implemented in `_land.py` only (not by
importing `frob.gates`, which depends on `frob.tickets`, never the
reverse, per docs/rework.md cycle-avoidance).

(2) `--push` option: `frob ticket land <id> --worktree <path> --push`
(new AppConfig field `ticket_land_push`, new argparse flag on the `land`
subparser in `src/frob/__main__.py`) runs `git push origin <branch>` for
root's current branch via `ticket_runner._push_after_land`, called ONLY
after `land()` returns `Ok` and ONLY when the report is not a dry run --
never on `--dry-run`, never after a failed land. Routed through
`guarded_subprocess_run` (T-0778's exec guard) so `FROB_DISABLE_EXEC=1`
refuses it too; a refused spawn or non-zero `git push` exit logs the
manual remedy and exits non-zero without attempting to unwind the
already-landed commit (there is nothing left to unwind by that point).

Scope note: the ticket's originally declared scope (src/frob/tickets/**,
src/frob/app/ticket_runner.py, docs/modules/tickets.md) did not include
src/frob/__main__.py or src/frob/app/config.py, which the --push CLI flag
structurally requires (argparse registration + AppConfig field, same
pattern as the existing --dry-run/--skip-mutation-evidence flags on this
subcommand) -- extended via `frob ticket scope --add` with a recorded
reason rather than touched silently. tests/test_ticket_land.py was
likewise added to scope (SCOPE001) to host the new tests in the existing
land test module, matching prior land-feature tickets in this lineage.

docs/modules/tickets.md's "frob ticket land" section gained step 9.75
(the regression sweep) and step 11 (--push), inserted at the exact points
in the existing numbered land procedure where they actually run.

Changed:
  src/frob/tickets/_land.py::_tick005_land_regressions
  src/frob/tickets/_land.py::_squash_and_splice_ledger (wires the sweep in)
  src/frob/tickets/_models.py::LandError.TerminalStateRegression
  src/frob/app/config.py::AppConfig.ticket_land_push
  src/frob/__main__.py::_add_ticket_land_parser (--push flag)
  src/frob/app/ticket_runner.py::_push_after_land
  src/frob/app/ticket_runner.py::_land (invokes _push_after_land)
  docs/modules/tickets.md (frob ticket land section, steps 9.75/11)
  tests/test_ticket_land.py (TestTick005LandRegressions,
    TestLandRefusesOnTerminalStateRegression, TestLandPushCliWiring,
    TestPushAfterLand)

Evidence: 11 new pytest node ids under tests/test_ticket_land.py, all
observed passing via `uv run pytest tests/test_ticket_land.py -q`
(137 passed total, up from 127 pre-change; no pre-existing test broken).
Acceptance criterion [0] bound to
TestLandRefusesOnTerminalStateRegression.test_land_refuses_and_unwinds_when_sweep_finds_a_regression
and TestPushAfterLand.test_real_land_pushes_the_current_branch.

Gates: `uv run frob check --ticket T-0631` chunked per docs/guides/
agent-playbook.md section 3b (prework/scope/coverage individually, then
lint/static/gates-fast/gates-native/gates-security stage groups) -- all
clean (0 unwaived errors) after `frob ticket sweep T-0631` refreshed the
pre-work sweep post scope-expansion. `uv run frob test --base main`
(touched-set) exit=0, PASS. `ruff check`/`ruff format --check`/`ty check`
clean on every touched file (both PATH ruff and `uv run ruff`).
`git diff main --diff-filter=D --stat` empty of anything outside this
ticket's scope.

Filed: none.
