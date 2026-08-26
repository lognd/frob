## Done report

T-2936: root-caused and fixed the actual crash. `src/frob/process/
_reap.py:137` was `def arm_parent_death_signal(sig: int = signal.
SIGKILL) -> bool:` -- a default argument is evaluated exactly once, at
MODULE LOAD (when the `def` statement itself executes), not per-call.
`signal.SIGKILL` does not exist on Windows at all, so this `def`
statement raised `AttributeError` the instant `frob.process._reap` was
imported -- before this function's own `sys.platform != "linux"` guard,
or any other line of its body, ever ran once. Every module that
transitively imports `frob.process` (essentially the whole CLI) failed
with it; `frob --help` itself crashed. Measured for real via T-2917's
own windows-latest CI job: 54s to failure, at `uv run frob natives
build`'s import of this module.

Fix: `sig: int | None = None`, resolved to `signal.SIGKILL` ONLY after
the platform guard passes. Also removed the now-unnecessary explicit
`signal.SIGKILL` argument at both real call sites (`_reap.py`'s own
forkserver-helper hook, `frob.gates.__init__`'s worker initializer) --
they now rely on the same safe internal default, and the now-dead
`import signal` in `gates/__init__.py` was removed.

Sweep for the same import-time-evaluated-platform-attribute pattern
(per the coordinator's explicit request, not just the one instance the
traceback named): grepped the whole `src/frob/**` tree for `def
...=signal.*`, module-level `NAME = os/signal/fcntl.ATTR` assignments,
and class-attribute/decorator-argument shapes of the same class. Found
NOTHING else -- this was the only default-argument instance repo-wide.
The two runtime call sites that passed `signal.SIGKILL` explicitly
(inside function bodies, evaluated at CALL time not import time) were
never import-crashing, but were hardened anyway for consistency/
defense-in-depth (see above).

Does PLATFORM001 (T-2919's new gate) catch this class? NO -- and this
is a finding about the gate, not just this bug. PLATFORM001's detector
(frob.gates._walk_lint._scan_platform_guards) only looks for `if
<name> is None:` guards on a name bound via the try/except-ImportError
probe idiom; a default argument evaluated unconditionally at `def` time
is a structurally different AST shape (no guard at all -- the crash
IS the absence of a guard) that this detector's population does not
cover. Not fixed here (a second, differently-shaped detector is a real
scope expansion, not a burn-the-existing-findings fix) -- filed T-2951
as a follow-up naming the gap directly, with this ticket's own
Default_ arg shape as its starting fixture.

Does frob now IMPORT on Windows? YES, per source analysis and the local
regression test (`test_default_arg_is_not_evaluated_at_def_time`
asserts `arm_parent_death_signal.__defaults__ == (None,)` directly --
the one place a crash-on-import regression here is provably impossible
to miss, since evaluating the assertion at all already proves the `def`
statement imported cleanly).

Does frob now RUN USEFULLY on Windows? NO, almost certainly not, and
this ticket does NOT claim otherwise. T-2917's own windows-latest CI
job only got 54s into the pipeline before this exact crash; fixing the
import does not retroactively prove anything about the ~150+ other
POSIX-only call sites/tests this repo has never run on Windows (T-2934's
own Done report fixed 4 of the fcntl-lock-shaped ones; T-2930 is
already triaging the 156 macOS-only pytest failures from the SAME
platform, a different OS but the same "never actually run there
before" starting condition). The real verdict on "does frob run
usefully on Windows" needs a fresh windows-latest CI run against this
fix, watched for real, not asserted.

### Changed
```
 src/frob/gates/__init__.py      |  9 ++++--
 src/frob/process/_reap.py       | 20 ++++++++++--
 tests/unit/test_process_reap.py | 67 +++++++++++++++++++++++++++++++++++------
 tickets/T-2936/ticket.md        | 30 ++++++++++++++++--
 4 files changed, 110 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_default_arg_is_not_evaluated_at_def_time` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_sig_none_resolves_to_sigkill_only_after_the_platform_guard` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_noop_without_env_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmForkserverHelperPdeathsigIfRequested::test_arms_when_env_var_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 23 error(s), 760 warning(s), 852 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
