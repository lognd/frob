## Done report

Changed:
- src/frob/gates/_gate_cache.py::GateRunReplay.age_s (removed the now-redundant
  per-site WIRE001 waiver; the underlying resolver gap it documented was
  already fixed generically by T-2746's _is_property/property_access_pattern
  in src/frob/gates/_wire.py)
- src/frob/gates/_gate_cache.py::GateRunReplay (added a scoped frob:waive
  AFFECT001, comment-only diff, no doc/behavior drift)
- tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess.test_property_read_as_keyword_argument_value_is_not_flagged
  (new permanent regression-guard test pinning the exact keyword-argument-value
  property-read shape that forced the age_s waiver)

Measurement (per this ticket's method requirements):
- Denominator of the false negative this ticket named: measured via
  `git grep -n "waive WIRE001"` across src/ -- exactly 1 live waiver citing
  this defect class (GateRunReplay.age_s, follow_up="T-2610"). No other
  live WIRE001 waiver in the tree names a property-attribute-access gap.
- The actual resolver defect (WIRE001 cannot see a @property's own plain-
  attribute-access caller) was already fixed generically by T-2746
  (confirmed on main via git log/git show -- src/frob/gates/_wire.py's
  _is_property/_PROPERTY_DECORATOR_RE/property_access_pattern, token/
  grammar-based: `_is_property` matches the decorator via a regex over
  the record's own AST-derived span opening line, and
  `property_access_pattern` is a symbol-qualified attribute-access regex
  scoped to records `_is_property` confirms, not a bare substring/lexical
  scan). This ticket's own diff is therefore the follow-on cleanup T-2746's
  own Suggested direction anticipated: removing the now-dead per-site
  waiver plus a permanent regression test for the specific shape
  (`age_s=replay.age_s`, a keyword-argument VALUE, not just the bare
  log-call-argument shape T-2746's own test file already covered) that
  forced it.
- Repo-wide WIRE001 finding count, `uv run frob check --only wire`:
  BEFORE (waiver present) and AFTER (waiver removed) are IDENTICAL --
  0 WIRE001 findings at GateRunReplay.age_s either way (1 unrelated
  pre-existing WIRE002 finding at src/frob/tickets/_unlanded.py in both
  runs, untouched by this ticket). This confirms the waiver's removal is
  safe: nothing regresses, nothing newly fires.
- Must-now-fire control: the new test
  test_property_read_as_keyword_argument_value_is_not_flagged builds a
  synthetic file reproducing the exact real-world shape
  (`_label(seconds=stamp.seconds)`) and asserts wire_gate does NOT flag
  it -- passes (4/4 in the test file, `pytest tests/unit/test_wire001_property_attribute_access.py`).
- Must-still-pass controls: the file's two pre-existing T-2746 positive
  controls (a property with no caller anywhere still fires; an ordinary
  non-property new method still fires) are unchanged and still pass --
  confirming this ticket's addition narrows nothing that was correctly
  firing before.

Evidence: tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_as_keyword_argument_value_is_not_flagged
(designated repro, forced via --designate-repro-force: this test is
confirmatory-only at the ticket's parent commit because the actual
resolver fix already landed as T-2746, the same posture T-2746 itself
recorded for its own BUG002 waiver at land time -- see reasoning
recorded in the ticket's designated_repro_changes/waive trail).

Filed: none (T-2610 was fully addressable by removing the stale waiver
this ticket was already the named follow_up for; no further open work
found).

Gates: `frob check --ticket T-2610` -- gate:AFFECT/gate:SCOPE/gate:PRE
clean (AFFECT001 waived for the comment-only diff, reasoning above);
every other FAIL in that run (ruff-check on tests/unit/verify/
test_backpressure.py, frob-cycle, gate:COV/DOC/LANG/TICK/WIRE) is
pre-existing repo-wide baseline noise identical across all four
--ticket T-2610 runs taken during this ticket's work, none of it in a
file this ticket touched.

### Changed
```
 frob.lock                                          | 14 +++++++
 src/frob/gates/_gate_cache.py                      | 18 ++++++---
 .../unit/test_wire001_property_attribute_access.py | 45 ++++++++++++++++++++++
 tickets/T-2610/ticket.md                           | 32 ++++++++++++++-
 4 files changed, 102 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_as_keyword_argument_value_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 581 warning(s), 847 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, I001@/home/logan/projects/frob/.claude/worktrees/t-2610-series/tests/unit/verify/test_backpressure.py, LANG003@src/frob/lang (facet=capability), LANG003@src/frob/lang (facet=docblock), LANG003@src/frob/lang (facet=dup), TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
