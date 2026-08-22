## Done report

Changed:
src/frob/gates/_mutation_evidence.py::_BugReproOutcome (added TIMEOUT)
src/frob/gates/_mutation_evidence.py::bug_repro_outcome_at_ref
src/frob/gates/_mutation_evidence.py::_run_designated_test
src/frob/gates/_mutation_evidence.py::_spawn_designated_test (new, ARCH103 split)
src/frob/gates/_mutation_evidence.py::_classify_designated_test_exit (new, ARCH103 split)
src/frob/app/ticket_runner/_verify.py::_bug_repro_outcome_message
src/frob/app/ticket_runner/_verify.py::_validate_designate_repro_at_parent
src/frob/app/ticket_runner/_verify.py::_evidence_check_repro
src/frob/app/config.py::AppConfig (added ticket_repro_timeout_s)
src/frob/app/_config_external.py (added ticket_repro_timeout_s to the from_external allowlist)
src/frob/_cli_parsers/_ticket/_closeout.py (added --repro-timeout-s)

Scope note: the ticket's original declared scope (`src/frob/tickets/
_evidence.py` alone) did not contain the actual repro-timeout machinery
-- `_BugReproOutcome`/`_run_designated_test`/`_BUG_REPRO_TIMEOUT_S` live
in `src/frob/gates/_mutation_evidence.py`, and the `--check-repro`/
`--designate-repro` CLI-facing messaging lives in `src/frob/app/
ticket_runner/_verify.py`, neither of which `_evidence.py` even
imports. Widened scope via `frob ticket scope --add` (the sanctioned
mechanism, not a silent expansion) to the files the fix genuinely
required, discovered incrementally as each dependency surfaced (a new
CLI flag needs `_closeout.py`'s parser + `config.py`'s pydantic field +
`_config_external.py`'s from_external allowlist -- WIRE001 caught the
last one when I initially missed it).

Fix:
  - New `_BugReproOutcome.TIMEOUT` member, distinct from `NO_VERDICT`.
    Every existing caller (`bug_repro_violations`, `must_still_pass_
    violations`) already gates via an ALLOWLIST check (`if outcome is
    not FAILED_AT_PARENT: return ()` / `if fix_outcome not in (PASSED_
    AT_PARENT, FAILED_AT_PARENT): continue`), so the new member falls
    into the safe "no violation, no false pass" bucket automatically --
    verified by reading both call sites, no change needed there.
  - `_spawn_designated_test` (new, split out of `_run_designated_test`
    for ARCH001's line-length ceiling, ARCH103-style) calls `frob.
    process._guard.guarded_subprocess_run` DIRECTLY instead of through
    `frob.gitio.run_argv` -- `run_argv` catches `subprocess.
    TimeoutExpired` internally and collapses it into the SAME
    `Err(GitError.GitFailed)` a spawn refusal or `OSError` produces, so
    a caller downstream of `run_argv` cannot distinguish "hit the
    budget" from "could not spawn at all". Catching the timeout HERE,
    before that collapse, is what makes TIMEOUT a real outcome instead
    of another shade of NO_VERDICT.
  - `bug_repro_outcome_at_ref` (the public entrypoint both `--check-
    repro` and `--designate-repro` call) gained a `timeout_s: float |
    None = None` keyword-only override, threaded down to `_run_
    designated_test`. `bug_repro_violations` (the land/close-time gate
    consumer) deliberately does NOT expose it -- a per-ticket override
    there would let a slow, never-actually-verified test just wait
    longer instead of surfacing TIMEOUT; the override is for the
    interactive/on-demand paths where a caller is actively watching.
  - New `--repro-timeout-s SECONDS` CLI flag on `frob ticket evidence
    --check-repro`/`--designate-repro`, threaded through `AppConfig.
    ticket_repro_timeout_s` -> both call sites in `_verify.py`.
  - `_bug_repro_outcome_message` gained a TIMEOUT branch: distinct
    wording naming the budget, recommending `--repro-timeout-s` or
    hand-verification + `--designate-repro-force`, never conflated with
    NO_VERDICT's generic "could not even collect" wording.
  - Did NOT auto-permit `--designate-repro-force` on TIMEOUT (the
    ticket's third "consider" item). Decided against it: a genuinely
    hanging/infinite-loop test would then silently force through with a
    machine-generated "timeout" reason, which is a WORSE signal than
    today's honest human-authored force reason -- the ticket's own
    must-still-refuse acceptance is about not creating exactly this
    kind of side channel. `--repro-timeout-s` is the safe lever instead.
  - Did NOT simply raise `_BUG_REPRO_TIMEOUT_S` (the ticket's explicit
    "do not just move the cliff" instruction).

Positive controls (all real subprocess runs against real git repos, no
mocking of the outcome itself):
  - must-distinguish/must-now-protect (acceptance [0]):
    `test_slow_test_exceeding_budget_is_timeout_not_no_verdict` commits
    a test that `time.sleep(5)`s, runs it with `timeout_s=0.2`, asserts
    `TIMEOUT` and NOT `NO_VERDICT`.
  - must-still-refuse (acceptance [1]):
    `test_fast_genuinely_failing_test_still_refused` commits a FAST
    test that genuinely PASSES at the parent (confirmatory-only shape),
    asserts `PASSED_AT_PARENT` and NOT `FAILED_AT_PARENT` -- BUG002's
    real check is unweakened by the TIMEOUT addition.
  - must-still-complete (acceptance [2]):
    `test_fast_genuinely_reproducing_test_completes_normally` commits a
    fast, genuinely-failing test, asserts `FAILED_AT_PARENT` through
    the normal path, no added friction.
  - CLI-level: `test_timeout_outcome_reports_distinctly_and_exits_
    nonzero` asserts the ERROR log record's label reads "T-0001
    TIMEOUT:" (never "NO_VERDICT:") and mentions `--repro-timeout-s`.
    `test_repro_timeout_s_is_forwarded`/`test_repro_timeout_s_survives_
    from_external` pin the flag actually reaching `bug_repro_outcome_
    at_ref` (the T-0749/WIRE001 precedent this file's own docstring
    names -- I hit exactly the WIRE001 gap the precedent warns about,
    on the first pass, and the gate caught it as intended).

Filed: T-2495 (add `may "exec"` to design/frob.strata's `gates` node
formally, once T-2487's live lease on that file clears; T-2480 waived
SELFAUDIT001 at the 3 sites the new direct `guarded_subprocess_run`
call triggered, with a reasoned justification -- the exec capability
was already effectively present transitively via `run_argv`, this only
moves which function issues the syscall).

Evidence:
tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict (accepts 0)
tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_timeout_outcome_reports_distinctly_and_exits_nonzero (accepts 0)
tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_failing_test_still_refused (accepts 1)
tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_reproducing_test_completes_normally (accepts 2)
tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_repro_timeout_s_is_forwarded (accepts 0)
tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_repro_timeout_s_survives_from_external (accepts 0)

Gates: `frob check --ticket T-2480` clean of new errors on every touched
file (repo-wide `gate:TICK` counts on `tickets.md` are pre-existing,
unrelated to this diff). `frob fmt --check` clean. Full test run across
`tests/test_gates_mutation_evidence.py`, `tests/gates/
test_bug_repro_at_ref_public.py`, `tests/unit/
test_ticket_runner_designate_repro.py`: 85/85 pass -- including the 3
pre-existing mock-call-signature tests updated to expect the new
`timeout_s=` keyword argument now forwarded on every call.

### Changed
```
 tickets/T-2480/ticket.md | 106 +++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 102 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_timeout_outcome_reports_distinctly_and_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_failing_test_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_fast_genuinely_reproducing_test_completes_normally` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_repro_timeout_s_is_forwarded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal::test_repro_timeout_s_survives_from_external` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2480, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
