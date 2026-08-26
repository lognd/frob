## Done report

Changed: tests/unit/verify/test_backpressure.py (I001 import-sort fix,
`ruff check --fix` applied)

Measured before fixing: `uv run frob check --only lint --ticket T-2899`
reproduced exactly the finding cited by the ticket -- 2 errors, I001 at
lines 156 and 169. Traced blame with `git log -- tests/unit/verify/
test_backpressure.py`: the file's last-touching commit is
7100396e8bf5f1beea1f6697cc29a4386b30b8bc (T-2361's land), which is the
exact commit the sweep cited. `git show` on that commit confirms it
added TestEffectiveProfileOrStandard's two test methods, each with a
local (function-body) import block that ruff's isort rule flags as
unsorted. This is a genuine regression from T-2361's land, not stale
pre-existing residue and not a rolling-baseline gap -- it reproduces
cleanly and the blame is unambiguous.

Fix: `ruff check --fix` on the one file (2 fixed, 0 remaining). Reran
`frob check --only lint --ticket T-2899`: 0 errors (I001 gone; the file
is otherwise pass). Reran the two new tests directly: both pass.

Duplicate ticket found: T-2898 files the IDENTICAL (rule, file) identity
from the same commit (7100396e8bf5f1beea1f6697cc29a4386b30b8bc), same
I001/test_backpressure.py finding, same body text verbatim -- two
sweep-filed tickets for one regression. `frob ticket work T-2899` warned
about this at start time. Dropping T-2898 as absorbed by this ticket
once T-2899 closes.

Evidence: tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_ok_passes_through,
tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_err_falls_back_to_standard

Filed: none new. T-2898 dropped as absorbed-by T-2899 (duplicate, not
new out-of-scope work).

Gates: frob check --only lint --ticket T-2899 clean (0 errors); the
15 pre-existing ruff-format warnings listed are unrelated files, not
touched by this ticket, not introduced by it.

### Changed
```
 tickets/T-2899/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_ok_passes_through` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_err_falls_back_to_standard` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 21 error(s), 469 warning(s), 847 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, LANG003@src/frob/lang (facet=capability), LANG003@src/frob/lang (facet=docblock), LANG003@src/frob/lang (facet=dup), PRE001@tickets/T-2899, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
