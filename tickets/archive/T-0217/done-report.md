## Done report

Changed:
- src/frob/strata/_threat.py::evaluate_threats (log line only; behavior
  unchanged) -- the `_log.info("threat: evaluated view=%r catalog=%d
  out_of_scope=%d -> %d violation(s)", ...)` line renamed and demoted to
  DEBUG: `_log.debug("threat: obligations evaluated view=%r catalog=%d
  out_of_scope=%d -> %d pre-discharge obligation(s) (not all become
  tickets; see caller's own post-discharge count/verdict)", ...)`, plus an
  inline comment explaining why (T-0217).
- tests/unit/strata/test_threat.py::TestEvaluateThreats::test_pre_discharge_count_log_is_honest_and_debug_level
  (new) -- caplog-based unit regression: asserts the log record's level is
  DEBUG, the message does not contain the misleading "violation(s)"
  wording, and does contain "pre-discharge obligation(s)".
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_threat_pre_discharge_count_never_reads_as_contradicting_output
  (new) -- CLI-level regression: runs `frob sys plan` against the existing
  `_MODEL` fixture and asserts the exact old contradictory substrings
  ("-> 0 violation(s)", "threat: evaluated view=") never appear in
  default-verbosity stdout+stderr.

Root cause: `evaluate_threats` (`_threat.py::evaluate_threats`, called by
both `frob sys plan`'s `_plan.py::_frontier_threats` and `frob sys doc`'s
DOC003 half `_sysdoc.py::audit_claim`) logs the COMBINED count of catalog
+ capability + discharge (+ effect, when bound) completeness violations --
this is a pre-discharge OBLIGATION count spanning four different
completeness checks, not a live-violation count. `_frontier_threats` only
turns the THREAT003 subset of that same set into planned obligation
tickets, so a nonzero pre-discharge count next to a "0 obligation
ticket(s) would be created" / a clean PROVED-style summary read as
contradictory even though nothing was wrong -- the two numbers answer
different questions (all pre-discharge obligations vs. THREAT003-only
undischarged-and-actionable ones). Fixed per the ticket's own two
suggested options, both applied: (a) renamed the line to describe what it
actually counts and explicitly note not all of it becomes tickets, and
(b) demoted from INFO to DEBUG since it is per-run diagnostic detail, not
a user-facing verdict.

Did NOT add a stdout-log-level verbosity dial to `frob sys plan`/`frob sys
doc` (T-0202's `-v`/`-vv` dial and `stdout_log_level` context manager are
`frob check`-only today, per `src/frob/logging/quiet.py`'s docstring and
`src/frob/__main__.py`'s `check_verbose` argument, which has no `sys`
equivalent) -- `sys` commands print all DEBUG/INFO lines unconditionally
regardless of level today, so the DEBUG demotion alone does not hide the
line from `frob sys plan`/`frob sys doc` output yet. That is consistent
with every other DEBUG/INFO line those two commands already print (e.g.
`digested ...`, `strata parse ok`, `plan: compiled N obligation
ticket(s)`) and is a separate, larger-scoped concern (wiring a verbosity
dial into `sys_runner.py`) than this ticket's diagnosed bug, which was
specifically the misleading WORDING of this one line, not its verbosity.
Filed no follow-up ticket for the dial since nothing in the sibling-repo
pilot gap asked for one and it is a new feature, not a bug fix -- flagging
here per playbook section 8 (disclose cuts) rather than silently
implying "hidden by default" is now true.

Coordination: did not touch `frob sys audit`'s `PROVED` output
(`_print_audit_report`/`_print_selfconform_report` in `sys_runner.py`,
T-0224's surface) or `_audit.py::_evaluate_family`/`evaluate_exhaustiveness`
-- confirmed via read that `sys audit` never calls `_threat.py::
evaluate_threats` (it uses the separately-parameterized, non-logging
`_evaluate_family` instead), so this fix cannot regress T-0224's
ASSUMED-vs-PROVED matrix rendering or T-0202's `check -v`/`-vv` dial
(neither call `evaluate_threats`, confirmed via `grep -rn
"evaluate_threats"` over `src/frob/`).

Evidence:
- `uv run pytest tests/unit/strata/test_threat.py -q -k pre_discharge` ->
  1 passed.
- `uv run pytest tests/system/test_cli_sys_plan.py -q` -> 6 passed (all
  tests in the file, including the new regression).
- `uv run pytest --collect-only -q` -> collected cleanly, no errors (ran
  from a `make core`-built worktree venv).
- `uv run frob test --base main` -> `run_selected: python exit=0
  duration=3.28s`, `[PASS] python exit=0 3.28s` over the touched-set
  selection (11 touched, 0 ripple), including both new test node ids.
- `uv run frob check --ticket T-0217` -> `pass gates 0 errors, 12
  warnings, 223 waived`; overall `frob check .` -> `[WARN] 0 errors 345
  warnings` (0 errors, no DRIFT002 anywhere in output).
- `git diff main --diff-filter=D --stat` -> empty (deletion-filter land
  rule, playbook section 9).
- Reverted `frob-core/Cargo.lock` / `strata-core/Cargo.lock` noise from
  `make core` before the final check (playbook process rule); re-ran
  `frob ticket sweep T-0217` (PRE001 was stale after the Cargo.lock
  revert) and `make coverage` (TEST006 stamp) before the final clean
  `frob check` run above.

Filed: none (no out-of-scope work discovered).

Gates: `frob check --ticket T-0217` clean (0 errors); the pre-existing
`TEST005` waiver on `evaluate_threats` at `src/frob/strata/_threat.py:1232`
("evaluate_threats 83.3% branch cover, debt T-0160") is unrelated debt
from before this change, not newly introduced, and unchanged by this diff.
