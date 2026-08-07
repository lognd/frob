## Done report

Fixed all four required behaviors of the close-time mutation-evidence
sweep's missing budget, root-caused where the loop actually lives
(src/frob/tickets/_mutation_evidence.py + src/frob/mutate/__init__.py --
widened scope from the ticket's declared
src/frob/gates/_mutation_evidence.py, a same-named but DIFFERENT file in
a different package that only consumes the sweep's output; see the
frob ticket scope --add reasons for exactly what and why).

1. BUDGET THE SWEEP -> UNMEASURED, not pass/fail.
   `check_ticket_mutation_evidence` now takes `sweep_budget_s` (default
   `_sweep_budget_s()`, env-overridable via FROB_MUTATION_SWEEP_BUDGET_S,
   90s out of the box) -- ONE deadline shared across the whole sweep
   (every file, every mutant), computed once and threaded through
   `run_mutations`' new `deadline_monotonic` down to `_run_mutants`'
   per-mutant check. A file cut short (mid-mutant-loop, or never even
   started because an earlier file spent the whole budget) is reported
   as `ConfirmatoryFinding(unmeasured=True, ...)` -- a NEW field,
   default False, never conflated with a genuine confirmatory-only
   verdict. `frob.gates._mutation_evidence._test016_unmeasured_message`
   gives this its own wording (never "confirmatory-only") so a human or
   agent reading TEST016's message cannot mistake "could not measure"
   for "measured and failing" -- T-1703's exact lesson.

2. WARN AT BIND TIME.
   `frob.tickets._evidence._warn_bind_time_mutation_sweep_cost`, wired
   into `add_evidence` right after a successful write: projects the
   SAME close-time cost (one bounded real timing run of the ticket's
   bound evidence-id set, times the cheap subprocess-free planned-mutant
   count for the ticket's touched files) and logs a WARNING naming the
   bound test ids and the projected seconds when it exceeds the sweep
   budget. Best-effort/advisory only -- never affects the write it runs
   after, degrades to silent no-warn on any failure (no touched files,
   exec disabled, spawn OSError).

3. PROGRESS REPORTING.
   `_run_mutants` now logs one INFO line per mutant attempted
   (`mutant N/M of <file> (line L, description)`), so a long sweep is
   visibly progressing rather than indistinguishable from a hang --
   directly answering what the ten-timeout incident could never answer.

4. NOT fixed by raising the timeout.
   The new budget (90s default) is SMALLER than the old worst-case
   ceiling (up to 720s), and the fix is an internal deadline producing
   an honest partial result, never a bigger constant that still
   eventually runs out with nothing to show.

Changed:
- src/frob/mutate/__init__.py::run_mutations (deadline_monotonic param)
- src/frob/mutate/__init__.py::_run_mutants (deadline check + progress log)
- src/frob/tickets/_mutation_evidence.py::ConfirmatoryFinding (unmeasured field)
- src/frob/tickets/_mutation_evidence.py::check_ticket_mutation_evidence (sweep_budget_s, shared deadline loop)
- src/frob/tickets/_mutation_evidence.py::_mutation_evidence_for_file (truncation detection)
- src/frob/tickets/_mutation_evidence.py::_sweep_budget_s (new)
- src/frob/gates/_mutation_evidence.py::_test016_message (branches on unmeasured)
- src/frob/gates/_mutation_evidence.py::_test016_unmeasured_message (new)
- src/frob/tickets/_evidence.py::add_evidence (wires the bind-time warning)
- src/frob/tickets/_evidence.py::_warn_bind_time_mutation_sweep_cost (new)
- src/frob/tickets/_evidence.py::_planned_mutation_sweep_mutants (new, ARCH001 split)
- src/frob/tickets/_evidence.py::_measured_bind_time_evidence_wall_clock_s (new, ARCH001 split)
- docs/modules/tickets.md's TEST016 section (sweep budget + bind-time projection prose; also fixed a pre-existing stale "90s" -> "30s" _TIMEOUT_S factual error found while editing this exact paragraph)
- design/frob.strata (declared the new fs.read/env.read capability edges SELFAUDIT001 flagged for the new code)

Evidence: 5 pytest node ids -- two exercise the real budget/truncation
path against `check_ticket_mutation_evidence` directly (zero-budget and
pre-expired-deadline shapes), one is the REQUIRED pathological-shape
reproduction (a bound evidence test that itself spawns a real
subprocess, run through the real sweep with a small nonzero budget,
asserting the whole call returns in well under 60s and comes back
unmeasured=True, not hung and not silently clean), and two cover the
bind-time warning (fires when projected cost exceeds budget; stays
silent when there is nothing to project).

Verification:
- `uv run pytest tests/test_tickets_mutation_evidence.py tests/test_gates_mutation_evidence.py tests/gates/test_mutation_evidence_err_branches.py tests/test_mutate.py tests/test_mutate_journal.py tests/test_ticket_evidence.py tests/test_tickets_evidence_cli.py tests/test_tickets_cmd_evidence.py tests/test_evidence_integrity.py -q` -- 194 passed, 1 skipped.
- `uv run ty check` / `uv run ruff check` / `uv run ruff format --check` on every touched .py file -- all clean.
- `uv run frob check --land-parity` (cache-bypassed) -- clean, 0 unscoped errors.

Filed: none new for this ticket's own work. (T-1726/T-1723 dropped/
absorbed in the prior session turn, T-1742 filed for the
pre-commit hook's merge-commit false-refusal found while merging main.)

Gates: frob check --land-parity clean, 0 unscoped errors. One waiver
added (WIRE001 on the shared test fixture `_repo_with_add_change`,
reasoned, follow_up="T-1727" -- every call site is a real test_* method
in the same file; T-1592/T-1558's cross-file-only reach rule does not
recognize same-file test-fixture reuse as "wired" even though it
demonstrably is, verifiable by reading the file directly).

### Changed
```
 tickets.md | 208 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 206 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_zero_budget_reports_unmeasured_not_confirmatory` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_mid_sweep_deadline_truncates_and_reports_unmeasured` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestWarnBindTimeMutationSweepCost::test_warns_when_projected_cost_exceeds_budget` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestWarnBindTimeMutationSweepCost::test_no_warning_when_no_touched_python_files` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_real_subprocess_spawning_evidence_stays_bounded_not_hung` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 835 warning(s), 726 waived
- error-findings: none (measured, zero errors)
