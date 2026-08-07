## Done report

Changed: src/frob/strata/_models.py::CrashContract (new, restart/retry/
recovers_from, mirrors Node.capacity's placement),
src/frob/strata/_models.py::Node.crash, src/frob/strata/_models.py::
Flow.timeout, src/frob/strata/_models.py::_AT_LEAST_ONCE/_IDEMPOTENT
(promoted from _facts.py so _crash.py can reuse the same join without
duplicating the string constants), src/frob/strata/_facts.py (import the
promoted constants, no behavior change), src/frob/strata/_errors.py::
StrataError.MissingTimeout/IncompatibleTimeout (new), src/frob/strata/
_crash.py (new module): CrashContractReport,
evaluate_crash_contracts + private helpers (_crash_bound_seconds,
_validate_recovery_sources, _validate_no_hang, _join_retry_idempotency,
_generate_crash_scenarios), src/frob/strata/__init__.py (export the new
symbols).

Design note for the reviewer: this ticket's declared scope
(src/frob/strata/**, tests/unit/strata/**) excludes strata-core/** and
docs/strata/**, unlike its phase-3 siblings T-0069/T-0070/T-0073 which
all include strata-core/** for exactly this kind of grammar work. The
surface syntax `on crash { restart within t; inflight fail retriable
within t'; state recovered from X }` requires new Rust parser grammar
(strata-core/src/parse.rs) to populate a NodeDecl field -- the existing
generic `attr key=value` escape hatch cannot carry a numeric duration
(its value must lex as an IDENT, letters-only) -- so no `.strata` source
text can populate `Node.crash`/`Flow.timeout` yet. Given the scope
boundary, this ticket implements the full kernel-level engine (all three
joined checks: recovery-source validation, no-hang, and the
crash-retry-idempotency join reusing `_facts.py`'s existing
at-least-once/idempotent diagnostic) against `KernelModel`/`Node`/`Flow`
constructed directly -- the same pattern `tests/unit/strata/
test_scenarios.py` already uses for several `_scenarios.py` cases -- and
leaves the AST/elaborator/grammar wiring for a follow-up ticket in scope
for strata-core. Filed T-0118 to fix T-0074's (and any sibling's) scope
definition; this ticket's own scope was left untouched.

Evidence: 13 pytest node ids above (all green), plus the full
`tests/unit/strata` suite (145 tests) green.
Filed: T-0118 (scope gap: T-0074 missing tickets.md/docs/strata in scope,
unlike phase-3 siblings; also flags the strata-core grammar follow-up
needed to make `on crash`/`timeout` surface-parseable).
Gates (corrected after reviewer verification -- the original "no new
warnings vs baseline" claim was checked only via total_errors/exit code,
not a diagnostic-count diff against main, and was wrong): `frob check
--json --only gates` on main (this branch's changes stashed, including
untracked files) reports 134 diagnostics. The first pass of this branch
reported 135 -- three genuinely new ones, all introduced by this diff:
(1) TEST002 on `evaluate_crash_contracts` -- the `frob:tests` directives
in tests/unit/strata/test_crash.py were placed as a comment immediately
above each `def test_...` line, which the comment binder
(`_find_enclosing`, T-0044's known bug) resolves to the enclosing TEST
CLASS rather than the test method, so the edge's `src` never matched a
real pytest node id. Fixed by moving each `# frob:tests ... kind="unit"`
line to be the first statement INSIDE the test method body instead of
above it, so the comment's span is contained by the method symbol, not
the class -- now 13/13 edges resolve and TEST002 clears for this symbol.
(2) PERF004 sorted()-in-loop at `_crash.py::_generate_crash_scenarios` --
the rule's coarse token heuristic reads `for node_id in sorted(crashable)`
inside the returned generator expression as a sort-per-iteration. Fixed
by hoisting `node_ids = sorted(crashable)` into its own statement before
the generator (matching the rule's own suggested remedy) instead of
waiving it, so no new diagnostic (even a waived "note") is added to the
count. (3) PERF003 nested-loop-with-equality at
`test_crash_scenario_re_checks_every_declared_claim` -- two list
comprehensions each paired with `==` tripped the two-`for`-plus-`==`
heuristic; restructured to unpack the single-element tuples directly
(`(scenario,) = report.scenario_results; assert scenario.scenario_id ==
...`) instead of comparing list-comprehension results, removing both
`for` tokens from the method. Re-verified: `frob check --json --only
gates` on this branch now reports exactly 134 diagnostics, and a
file/rule-id diff against the main-baseline set is empty (only line-
number drift from the _AT_LEAST_ONCE/_IDEMPOTENT import move in
_facts.py, no new or removed rule ids). `pytest tests/unit/strata` still
145 green. `frob check` (no ticket scope) exits 0. `frob check --ticket
T-0074` still carries exactly one residual SCOPE001 on tickets.md,
unavoidable via the required `frob ticket start/evidence/sweep` CLI
mechanics under this ticket's under-scoped definition (see T-0118); not
code scope creep.
