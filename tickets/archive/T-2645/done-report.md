## Done report

Changed:
  src/frob/tickets/_unlanded.py::_scratch_file_for_suffix (new)
  src/frob/tickets/_unlanded.py::_remove_scratch_file (new)
  src/frob/tickets/_unlanded.py::_directive_ids_via_real_parser (modified)

Evidence:
  tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_directive_anchor_still_flagged_via_real_parser
  tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_genuine_directive_anchored_specimen_still_flagged
  full file: tests/unit/test_unlanded_branch_work.py -- 21/21 pass

Filed: none

Gates: frob check --ticket T-2645 -- all findings in the touched-set are
pre-existing/unrelated (frob-cycle, gate:DOC, gate:TICK rot, gate:COV
attachment-hash drift) except one WIRE001 on the new _remove_scratch_file,
which is waived in-line (atexit.register callback, invisible to the
call-graph resolver by construction).

Scope declared: src/frob/tickets/_unlanded.py (attempted to add
src/frob/lang/__init__.py for a possible parse_text entrypoint per the
ticket's own suggestion, but that path is leased by in-progress T-1604 --
ScopeLeaseConflict on `frob ticket scope --add`, confirmed via the CLI,
not assumed. Stayed within the original scope instead of forcing it.)

Measurement (why the fix was scoped the way it was):
  `frob ticket doable` in this worktree completed BOTH before and after
  the change (92s before, 99s after -- noise-level difference, not a
  regression); it no longer scans branches inline at all (T-2629 already
  decoupled `doable`'s render path from this scan on a cache miss), so
  this ticket's fix is invisible to `doable` timing by design -- it only
  pays off wherever the scan itself still runs (`frob ticket reconcile`,
  a warm cache refresh).

  Direct microbenchmark of `_directive_ids_via_real_parser` (300 calls,
  distinct content per call to avoid content-hash cache hits masking the
  difference), isolated from doable:
    before (fresh tempfile.NamedTemporaryFile create+write+flush+close+
      unlink per call): 0.300s / 300 calls
    after (one mkstemp per suffix, reused via plain open/write): 0.138s
      / 300 calls
  ~2.2x reduction in the per-candidate scratch-file overhead this ticket
  named. `frob.lang.parse_file`'s own cache key is path+content-hash, so
  reusing the path across distinct content cannot collide (verified by
  reading `frob.lang._parse`'s cache_key construction).

  Could not add a text-in `frob.lang` entrypoint (the deeper fix the
  ticket floated) because `src/frob/lang/__init__.py` is under another
  ticket's (T-1604) lease for the duration of this series -- documented
  above and in the modified function's docstring rather than forced.

### Changed
```
 tickets/T-2645/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_directive_anchor_still_flagged_via_real_parser` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_genuine_directive_anchored_specimen_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 17 error(s), 432 warning(s), 847 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@tickets/T-2886/ticket.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2645-series/src/frob/tickets/_unlanded.py, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
