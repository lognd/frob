## Done report

Verified-first, no code change needed: the double-compute this ticket
describes is already mooted by T-0423's run-scoped memoization
(`frob.check._memo.memoize_per_run` on `frob.arch.analyze_project`,
landed in a prior commit on this branch's history). Measured
`uv run frob check` gate timing shows `archgate=0.00s` (was ~112.81s at
ticket-file time) -- `gates/_arch.py::arch_gate` still calls
`analyze_project` directly (unchanged), but within one `frob check`
process the second call is a memo hit against `_run_arch`'s (the
frob-arch stage) first call, so `analyze_project`'s real body runs
exactly once per check. `tests/unit/test_memo.py::
test_analyze_project_second_call_is_memo_hit` already asserts this
invariant (1 hit, 1 miss) and passes.

The specific dead helper this ticket names,
`_arch_violations_from_suggestions`, no longer exists under that name --
T-0375 built (and wired) its replacement, `check/_python.py::
_arch001_violations`, used by `_arch_long_function_waived_symrefs` for
the ARCH001 waiver cross-reference. `frob.gates._dead_symbols` (T-0422's
DEAD001 gate, built after this ticket was filed) now statically catches
exactly this class of "written to fix a bug but never wired" helper
going forward -- it cites this ticket's motivating case in its own
docstring.

Dup: verified `dup_gate` (src/frob/gates/__init__.py::dup_gate) returns
early when `[dup].enforce` is off (repo default), so it does not run
`find_clones` at all in a default check -- no double-run there either,
per the ticket's own "verify" instruction.

No source changes made; this ticket's premise was already resolved by
T-0423 (memoization) and T-0375/T-0422 (helper rename + wiring, general
DEAD001 gate). Closing with the timing/test evidence above rather than
touching already-correct code.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
