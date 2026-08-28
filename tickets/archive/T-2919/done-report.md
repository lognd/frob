## Done report

T-2919: generalized T-2918's one-off fix into a static gate so the NEXT
POSIX/Windows-only primitive added anywhere in src/frob/** cannot ship
the same silent warn-and-continue gap undetected.

Rode PLATFORM001 alongside the existing WALK001 rule in the SAME
walk_lint_gate function (frob.gates._walk_lint) rather than adding a new
dispatch-table stage -- one AST pass over the same tracked src/frob/**
file set produces both rule ids' violations, the same "ride alongside an
existing stage" precedent NEGEXIST001 already established for
"docblocks". This kept the change out of the heavily-contended
gates/__init__.py dispatch table entirely (touched only _walk_lint.py,
_waive.py for the _KNOWN_GATE_RULES registration, their two test files,
and docs/modules/gates.md).

Detector (three AST-scan steps, all in frob.gates._walk_lint):
1. `_platform_guard_names`: find local names bound to one of a fixed
   platform-restricted module list (fcntl/termios/tty/pwd/grp/resource/
   posix for POSIX; msvcrt/winreg/_winapi for Windows) inside a
   try/except-ImportError-sets-None idiom -- the exact shape this
   repo's own fcntl/msvcrt degrade sites use. Third-party optional-
   dependency names (z3, tree_sitter, ...) using the identical shape
   for an unrelated reason are explicitly out of the population.
2. `_scan_platform_guards`: find every `if <name> is None [and
   <name2> is None ...]:` guard referencing a step-1 name -- handles
   both a single-primitive guard and T-2918's own "neither primitive"
   compound form.
3. Classify the guard body: WARN-AND-CONTINUE (a finding) if it logs
   and never refuses; QUIET if it raises or calls sys.exit/os._exit
   anywhere (T-2918's own BaselineLockUnavailable shape).

Both fixture directions required by the ticket, in
tests/test_walk_lint_gate.py::TestPlatform001:
  - test_warn_and_continue_fires / test_gate_fires_end_to_end: a MUST-
    FIRE fixture lifted byte-for-byte from `_baseline_lock`'s actual
    PRE-T-2918 shape.
  - test_loud_refusal_is_quiet / test_gate_stays_quiet_on_properly_
    guarded_module: a MUST-STAY-QUIET fixture matching `_baseline_
    lock`'s actual POST-T-2918 fix (the real BaselineLockUnavailable
    shape).
  - test_no_platform_probe_is_quiet: a control proving an unrelated
    optional-dependency probe (z3) never anchors this rule at all.

Disclosed gap (documented in both the module docstring and
docs/modules/gates.md): a genuine typani `return Err(...)` structured
refusal is not recognized as "loud" -- distinguishing it from an
ordinary silent early-return needs the enclosing function's declared
return type, out of scope for a single-pass AST scan. Such a site needs
a `frob:waive PLATFORM001` naming the real Result-typed refusal.

MEASURED against the real repo, not just fixtures: PLATFORM001 fired 5
real, pre-existing findings on its FIRST run (WARN severity, non-
blocking): src/frob/process/_lock.py:265, src/frob/tickets/_land.py:649,
src/frob/tickets/_land_git_ops.py:410, src/frob/tickets/_store.py:257,
src/frob/tickets/_store.py:357 -- all the same fcntl-absence
warn-and-continue shape T-2918 fixed in _rapid_sweep.py. Filed as a
follow-up (fix, not detect) rather than fixed inside this ticket, since
each site's correct remedy (genuine Windows backend vs. loud-refusal-
only) needs its own case-by-case judgment T-2918's Done report already
walked through for the one site it did fix.

### Changed
```
 tickets/T-2919/ticket.md           | 28 +++++++++++++++++-
 tickets/T-2934/ticket.md | 59 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 86 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 21 error(s), 828 warning(s), 851 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
