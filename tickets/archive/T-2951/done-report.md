## Done report

Added PLATFORM001 shape 4 (`_scan_import_time_platform_evals`,
`src/frob/gates/_walk_lint.py`): a platform-restricted attribute
(any attribute of a whole-module-restricted name -- fcntl/termios/
tty/pwd/grp/resource/posix/msvcrt/winreg/_winapi -- or a POSIX-only
`signal.SIG*` name) referenced in a `def`'s default argument value, a
module/class-level constant assignment, or a decorator call keyword
argument -- the exact shape T-2936 fixed by hand
(`arm_parent_death_signal(sig: int = signal.SIGKILL)`) that neither
the original `X is None` scan nor either T-2944 shape ever caught,
since there was no guard construct of any kind for those scans to
classify.

Two guard shapes stay quiet, both because Python itself never
evaluates the restricted attribute unconditionally: an attribute
reached only through one arm of an `ast.IfExp` ("ternary"), since
Python evaluates only the chosen branch; and a `def`/`Assign` nested
inside a real `if`/`try` block at module or class scope, which the
scan's own `_unconditional_body_blocks` helper never yields in the
first place (only the Module's own top-level statements and every
unconditionally-reachable `ClassDef`'s own direct body are walked).

Measured repo-wide PLATFORM001 count: 0 before this change, 0 after
(`walk_lint_gate` run directly against the worktree root) -- T-2936's
real site was already fixed by hand before this rule existed to
catch it, so there was no batch of new findings to triage.

Fixtures lock both directions for all four named shapes in
`tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval`:
- must-fire: `test_default_arg_fires` (T-2936's own pre-fix shape,
  byte-for-byte), `test_module_constant_fires`,
  `test_class_attribute_fires`, `test_decorator_kwarg_fires`
- must-stay-quiet: `test_guarded_default_arg_is_quiet` (T-2936's own
  post-fix `sig: int | None = None` shape), `test_ternary_guarded_
  constant_is_quiet` (`IfExp`-guarded constant), `test_if_guarded_
  def_is_quiet` (whole `def` nested inside a real `if
  sys.platform != "win32":` block), `test_body_reference_is_quiet`
  (restricted attribute read only inside a function body, never a
  default/module/class constant)
- `test_gate_fires_end_to_end` -- the full `walk_lint_gate` pass over
  a synthetic tracked repo

`docs/modules/gates.md`'s PLATFORM001 section documents shape 4
(scope widened to include this file via `frob ticket scope --add`,
consented via the resulting scope-closure warnings which name only
pre-existing, unrelated anchors elsewhere in the same page).

One real self-inflicted bug caught and fixed mid-ticket: the first
placement of the new violation function sat directly between two
halves of the existing combined WALK001+PLATFORM001 `frob:doc`/
`frob:tests` directive block above `walk_lint_gate`, silently
splitting it and rebinding half the block onto the new private
helper -- exactly the T-0297 shape `COV005` exists to catch, and it
did (see commit 4743b1013). Fixed by moving the new function well
away from that block instead of masking the finding.

Changed:
- src/frob/gates/_walk_lint.py::_restricted_attr_dotted_name (new)
- src/frob/gates/_walk_lint.py::_restricted_attrs_unguarded (new)
- src/frob/gates/_walk_lint.py::_unconditional_body_blocks (new)
- src/frob/gates/_walk_lint.py::_scan_import_time_platform_evals (new)
- src/frob/gates/_walk_lint.py::_platform001_import_time_violation (new)
- src/frob/gates/_walk_lint.py::walk_lint_gate (wired the new scan in)
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval (new)
- docs/modules/gates.md (PLATFORM001 section: shape 4 documented)

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-2951` clean (0 errors touching this
ticket's scope, confirmed via `--only prework`/`--only coverage`/
`--only tickets` with `FROB_NO_GATE_CACHE=1`, plus a repo-wide
`--only coverage` pass showing zero COV002 findings on either
changed file). `frob check --land-parity` (pre-fix run) surfaced the
COV005 rebind and both COV002 findings this report's fix addresses;
a post-fix `--land-parity` timed out under fleet load (T-2473
advisory: another check was already running on this host) but the
targeted `--only coverage` re-run confirms zero errors on either
touched file. All 25 `--land-parity` findings from the pre-fix run
that remain are pre-existing and outside this ticket's scope (ARCH103
in `_new_renumber.py`, COV001/COV007/SYS003/TEST001 in
`scripts/branch_stranded_work_analysis.py`, COV004 stale ticket
attachment shas, CYCLE001, DOC002/DOC005/DOC006, LARGE001, PII012,
SELFAUDIT001, TICK004).

### Evidence
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_default_arg_fires`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_module_constant_fires`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_class_attribute_fires`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_decorator_kwarg_fires`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_guarded_default_arg_is_quiet`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_ternary_guarded_constant_is_quiet`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_if_guarded_def_is_quiet`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_body_reference_is_quiet`
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_gate_fires_end_to_end`

Full `tests/test_walk_lint_gate.py` file: 36 passed, 0 failed
(`pytest tests/test_walk_lint_gate.py -p no:cacheprovider -q`).

### Changed
```
 docs/modules/gates.md        |  59 ++++++++++++
 src/frob/gates/_walk_lint.py | 211 ++++++++++++++++++++++++++++++++++++++++++-
 tests/test_walk_lint_gate.py | 142 +++++++++++++++++++++++++++++
 tickets/T-2951/ticket.md     |  19 +++-
 4 files changed, 426 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_default_arg_fires` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_module_constant_fires` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_class_attribute_fires` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_decorator_kwarg_fires` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_guarded_default_arg_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_ternary_guarded_constant_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_if_guarded_def_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_body_reference_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_gate_fires_end_to_end` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 23 error(s), 784 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
