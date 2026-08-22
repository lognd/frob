## Done report

Changed:
src/frob/gates/_pii_structural/_emails.py::_pii011_violation (symref path prefix)
src/frob/gates/_pii_structural/_emails.py::_is_reserved_test_domain_email (single-char-TLD exemption)
src/frob/gates/_pii_structural/_emails.py::_joined_comment_continuation (new)
src/frob/gates/_pii_structural/_emails.py::_line_or_block_marks_fake_email (new)
src/frob/gates/_pii_structural/_emails.py::_line_marks_fake_email (multi-line marker join)
src/frob/gates/_pii_structural/_keywords.py::_pii012_violation (symref path prefix)
src/frob/gates/_pii_structural/_keywords.py::_DirectiveContinuationTracker (new, extracted from _scan_comment_keywords for ARCH001)
src/frob/gates/_pii_structural/_keywords.py::_scan_comment_keywords (directive-continuation exclusion)
src/frob/gates/_pii_structural/_python_fields.py::_pii010_violation (symref path prefix)
tests/test_pii_structural_gate.py::TestSymrefPopulation (4 assertions updated to the corrected path::qualname shape)
tests/test_pii_structural_gate.py::TestSymrefPathPrefix (new)
tests/test_pii_structural_gate.py::TestDirectiveCommentContinuationExcluded (new)
tests/test_pii_structural_gate.py::TestSingleCharTldEmail (new)
tests/test_pii_structural_gate.py::TestWrappedFakeEmailMarker (new)

Re-triage summary: measured 21 unwaived PII010/011/012 findings at
pickup (not the ticket's stale 20-finding disclosure -- re-counted per
the ticket's own instruction). All 21 fell into 4 groups, each a single
detector defect, not 21 independent judgment calls:

1. (majority, ~19 findings) `enclosing_qualname`'s producers
   (`_pii010_violation`/`_pii011_violation`/`_pii012_violation`) emitted
   a bare dotted qualname with no `path::` prefix, but `Violation.
   symref`'s own documented contract (and every DSL-bound `waiver.src`)
   is `path::qualname` -- `_match_waiver_by_symref`'s exact-match could
   never succeed for ANY PII010/011/012 finding with a real symref.
   Fixed by prefixing `rel_path` in the three `_piiXXX_violation`
   helpers (the one place both values are already in scope).
2. A `frob:waive` directive's own wrapped `reason="..."` text (this
   repo's multi-line-comment convention) restates the very keyword it
   explains away (e.g. "not a mailing/contact address"), self-
   triggering a NEW finding on the waiver comment's own continuation
   line -- a line outside the target symbol's AST span, so no waiver
   could ever suppress it. Fixed: `_scan_comment_keywords` now excludes
   a directive's continuation lines, not just its first line
   (`_DirectiveContinuationTracker`).
3. Test git-identity email fixtures shaped `a@b.c`/`t@t.t` -- no real
   DNS TLD is 1 character, so this is the same structural non-personal
   guarantee `_RFC2606_RESERVED_EMAIL_DOMAINS` already rests on for
   `example.com`. Fixed: `_is_reserved_test_domain_email` now also
   exempts a single-character TLD.
4. An existing `frob:secret-fake reason="..."` marker whose reason
   wraps across 2 physical comment lines was invisible to `_line_marks_
   fake_email`'s same-line-or-line-above regex (it could see the marker
   keyword on one line and the closing quote on another, matching
   neither). Fixed: the marker check now reconstructs a wrapped
   continuation chain before searching.

2 sites remained genuinely unfixable within this ticket's scope
(`src/frob/gates/_pii_structural/**`) because the fix lives in a
different file: `src/frob/serve/_socketd.py:530` (a waiver bound by the
comment-binding DSL to the wrong following symbol -- a DSL question,
not a detector question) and `tests/test_capability_registry.py:902`
(a plain missing waiver, false positive on "secretsmanager"). Filed as
a follow-up rather than expanded scope.

No blanket/generic waivers were added anywhere -- every disposition
above is a root-cause fix to the DETECTOR (matching precision, comment
continuation, TLD structural fact, marker reconstruction), verified by
before/after re-measurement plus positive-control tests in both
directions (false positive stops firing AND a planted genuine
violation/still-failing case still fires) for every one of the 4
fixes.

Evidence: 10 pytest node ids (tests/test_pii_structural_gate.py, see
`frob ticket show T-2712`) plus the full existing
tests/test_pii_structural_gate.py suite (130/130 passed) as regression
coverage for the changed shared helpers.

Filed: T-2741 (renumbers at land) -- the 2 out-of-scope
sites above.

Gates: `frob check --json --no-cache --ticket T-2712` clean for every
file this ticket touched (no ARCH/COV/TEST/SEC/ruff finding on
_emails.py, _keywords.py, _python_fields.py, or
tests/test_pii_structural_gate.py in the final run). Remaining errors
in the full unscoped run are pre-existing and unrelated (import cycle,
ticket-ledger coverage, doc drift on unrelated modules).

### Changed
```
 tickets/T-2712/ticket.md           | 21 ++++++++++++-
 tickets/T-2741/ticket.md | 62 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 82 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestSymrefPathPrefix::test_pii010_symref_carries_path_prefix` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPathPrefix::test_pii011_symref_carries_path_prefix` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPathPrefix::test_pii012_symref_carries_path_prefix` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSymrefPathPrefix::test_module_level_symref_stays_none_with_path_prefix_fix` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestDirectiveCommentContinuationExcluded::test_wrapped_directive_reason_does_not_self_trigger` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestDirectiveCommentContinuationExcluded::test_unwrapped_ordinary_comment_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSingleCharTldEmail::test_single_char_tld_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestSingleCharTldEmail::test_two_char_tld_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestWrappedFakeEmailMarker::test_wrapped_marker_reason_discharges` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestWrappedFakeEmailMarker::test_unmarked_realmail_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 37 error(s), 791 warning(s), 695 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2712, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
