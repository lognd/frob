## Done report

Root cause per test:

1. tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
   -- CODE-adjacent behavior was fine (render_lint_gate's gitless-target
   WARN-not-ERROR severity itself never regressed); the TEST's own rebind
   trick was broken by test-ordering/caching, not by any severity
   promotion. `frob.logging.logger._init()` only re-runs `dictConfig`
   (rebinding stream handlers to the CURRENT sys.stderr/capsys) the first
   time `get_logger()` sees `_initialized is False`. The test cleared the
   guard AFTER already importing `frob.gates._render_lint` (whose own
   module-level `get_logger(__name__)` call had already re-armed
   `_initialized = True` using whatever sys.stderr was live at that
   import), so the clear was a no-op: nothing ever called `get_logger()`
   again afterward, so `dictConfig` never re-ran against the
   capsys-patched stream. Verdict: TEST fix (order of operations was
   backwards). Fixed by clearing the guard and immediately calling
   `get_logger()` directly -- forcing the rebind deterministically,
   independent of whichever module happens to have imported
   `_render_lint` first (isolation vs full-file run no longer differ).

2. tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
   -- two independent causes, both confirmed by scaffolding a fresh
   project in a tmp dir and running real `frob check` against it:
   a) `ty`'s own upward-directory-walk project/venv discovery has no way
      to pin itself to the scaffold root (`--project` only changes the
      walk's starting point per `ty check --help`); a target nested under
      an ancestor directory that happens to contain an unrelated
      `pyproject.toml`/`.venv` (reproduced against a stray
      `/tmp/pyproject.toml` + `/tmp/.venv` left by other tooling on this
      box) silently resolves imports/dependencies against THAT ancestor
      instead of the real target -- verified by moving the stray files
      aside (ty passed) and back (ty failed again), and by scaffolding
      one level under `$HOME` (always passed) vs. several levels under
      `/tmp` (failed until the fix). This is a genuine `_run_ty`
      robustness gap, not a severity promotion, and not scaffold-template
      specific -- any nested project could hit it. Verdict: CODE fix.
      `_run_ty` (src/frob/check/_python.py) now always passes
      `--extra-search-path <root>/src` (when a src-layout exists) and
      `--python <root>/.venv` (when a project-local venv exists), making
      first-party and third-party resolution hermetic to `root`
      regardless of ancestor-directory contents.
   b) Once ty passed, a second, unrelated failure surfaced: B9
      (T-0541, PRE001/SCOPE001) correctly fires as an ERROR when the
      working diff touches non-ledger/non-`.frob` files with no
      derivable active ticket. The fixture ran `frob check` on branch
      `main` immediately after `uv sync` (writes `uv.lock`) and
      `frob check --stamp-coverage` (writes the deliberately-committed
      `frob-coverage.lock.json`, T-0545) without ever committing those
      two real, meant-to-be-tracked artifacts -- so the working diff
      always had untracked non-exempt files with no ticket, exactly the
      B9 contract it exists to catch. This is not a template defect and
      not an unreasonable gate for a downstream project once it adopts
      frob's ticket workflow (which the scaffold template does, via
      `tickets.md`); it is a missing "commit your lockfiles" step in the
      fixture's simulated real-user workflow. Verdict: TEST fix (added a
      `git add -A && git commit` step between `--stamp-coverage` and the
      final `frob check`, mirroring the real workflow the gate expects).

Coordinator follow-up: land refused on TEST016 for the two Div-swapped
mutants at src/frob/check/_python.py:138/141 (`scan / "src"` ->
`scan * "src"`, `scan / ".venv"` -> `scan * ".venv"`). The structural-FP
justification for the SYSTEM evidence held (that evidence exercises
`_run_ty` only indirectly through the separately-installed global `frob`
binary, which a dev-tree source mutation cannot reach), but per the
coordinator's direction these mutants ARE killable at the unit level.
Added `tests/unit/test_check_tool_unavailable.py::
TestTyHermeticRootResolution` (two tests: one asserting the constructed
argv contains `--extra-search-path <root>/src` and `--python <root>/.venv`
verbatim when both directories exist, one asserting neither flag appears
when they don't), scoped in via `frob ticket scope T-0996 --add
tests/unit/test_check_tool_unavailable.py`. Hand-verified both kills by
manually re-applying each mutation in turn (`scan / "src"` ->
`scan * "src"`, then reverted, then `scan / ".venv"` -> `scan * ".venv"`,
then reverted) and confirming `TestTyHermeticRootResolution` fails with
the exact `TypeError: can't multiply sequence by non-int of type
'PosixPath'` under each mutant, and passes clean once reverted (`git diff`
confirmed no residual change after the hand-verification). Bound both new
node ids as evidence via `frob ticket evidence T-0996 ... --accepts 0`;
`--skip-mutation-evidence` is no longer needed for this ticket.

Also discovered mid-investigation (informational, not fixed): the
machine's global `frob` binary (`~/.local/bin/frob`, what this test
deliberately targets per its own docstring) was stale at 0.9.0 against
this worktree's 0.184.0 dev source -- `make install-tool`'s `--extra
serve` flag is rejected by the installed `uv 0.11.19` (no `--extra`
support for `uv tool install` in that version); reinstalled without
`--extra serve` to validate this ticket (`uv tool install --force
--reinstall . --with ./strata-core --with ./frob-core`). Left as an
observation for whoever owns the Makefile/uv-version pairing; out of
T-0996's scope (`src/frob/**` + the two named test files) to fix the
Makefile itself.

Changed:
- src/frob/check/_python.py::_run_ty
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity.test_render_lint_gate_warns_not_errors_on_gitless_root
- tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
- tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution (new)

Evidence:
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root -- green in isolation (-n0 and default -n auto) and in the full tests/system/test_cli_check.py file run.
- tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately -- green in isolation, including a real scaffold-and-check pass verified manually against two fresh scaffolds (a stray-/tmp-polluted location and a clean $HOME location) both ending in `frob check` exit 0 / "0 errors".
- Full `tests/system/test_cli_check.py tests/system/test_scaffold_dx.py` run together: 38 passed.
- `uv run frob test --base main`: touched-set selection (8 files) ran tests/system/test_cli_check.py, tests/system/test_scaffold_dx.py, and the three unit tests bound to `_run_ty` -- exit=0, all 5 recorded stable.
- `uv run frob check --ticket T-0996` (chunked by --only stage-group per playbook 3b, then whole): 0 errors across lint/static/gates-fast/gates-native/gates-security and the combined run.
- Full `tests/system/` suite run: the two target tests are green; 9 pre-existing failures remain in unrelated files (test_cli_evidence_enforcement.py, test_cli_sys_audit.py, test_cli_ticket_worktree_root.py, test_cli_ticket_land.py, test_cli_ticket.py, test_system.py) -- none touch _run_ty, the render-lint gitless path, or the scaffold pipeline; confirmed out of this ticket's scope/diff and not introduced by this change.

- tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_extra_search_path_and_python_pin_to_root and ::test_no_src_or_venv_omits_the_pinning_flags -- both pass clean; both hand-verified to fail (TypeError, matching the mutant's actual runtime effect) under each of the two Div-swap mutants in turn, confirming both TEST016 survivors are now killed by named evidence.

Filed: none.

Gates: frob check --ticket T-0996 clean (all stage groups pass, 0 errors).

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_extra_search_path_and_python_pin_to_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_no_src_or_venv_omits_the_pinning_flags` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
