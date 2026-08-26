## Done report

Fixed three misfiring frob-suggest nudge rules in .claude/hooks/frob-suggest.py,
mirroring the existing negative-pattern design used by unscoped-pytest /
unscoped-symbol-search:

- handrolled-floor-count: added a negative pattern that stays quiet when the
  piped command mentions something matching a rule id (`[A-Z]{3,12}[0-9]{3}`),
  since a rule-id grep is listing findings, not counting them.
- raw-find-name: added a negative pattern that stays quiet when the find root
  is a concrete subdirectory (a real path segment before an internal `/`),
  since that cannot descend into .venv/, build artifacts, or a sibling
  worktree the way the rule's stated rationale describes.
- raw-worktree: changed the recommendation from the EnterWorktree tool to
  `uv run frob ticket work T-XXXX`, and added an explicit warning against
  EnterWorktree (pins the whole session cwd, hard-blocks concurrent agents,
  refuses outright from a subagent).

Audited the other 8 rules (11 total minus these 3) for the same
must-fire/must-stay-quiet test gap:

- Lacked ANY must-stay-quiet test: make-target, hand-edit-ledger,
  unscoped-pytest, raw-linters, raw-worktree, raw-coverage, recursive-grep,
  unscoped-symbol-search, raw-find-name (9 of 11 -- everything except
  handrolled-floor-count and handrolled-fleet-probe, which already had
  negative-case tests from T-2031).
- Demonstrated two more genuine false positives while auditing and fixed
  them the same way:
  - hand-edit-ledger: the substring match had no trailing boundary, so an
    unrelated file like `tickets.md.example` false-positived
    (`sed -i 's/x/y/' docs/tickets.md.example`). Added `(?![\w.])` after the
    literal.
  - recursive-grep: identical false-positive shape to raw-find-name -- no
    negative pattern at all, so a scoped `grep -rn 'foo' src/frob/strata`
    blocked even though it cannot walk .venv/worktrees. Added the same
    concrete-subdirectory negative pattern.
- make-target, raw-linters, raw-coverage: no demonstrable false positive
  found (scoping does not change the intended behavior for these three, per
  the playbook's own "never run coverage/linters yourself" posture).
  unscoped-pytest and unscoped-symbol-search already had a working negative
  pattern, just no test exercising it.
- Filed T-2927 ("frob-suggest: add missing must-stay-quiet
  fixtures for 5 rules") to add regression coverage for make-target,
  raw-linters, raw-coverage, unscoped-pytest, unscoped-symbol-search --
  no functional fix demonstrated for these, so left as a documented test-gap
  ticket rather than guessing at a change.

Every one of the three T-2908 rules, plus the two additionally-fixed rules,
now has both a must-fire and a must-stay-quiet test in
tests/test_hook_frob_suggest.py (10 new tests total). Verified BUG002 repro
via --check-repro: committed the test file alone first (hook unchanged),
confirmed test_hand_edit_ledger_stays_quiet_on_an_unrelated_file genuinely
FAILED_AT_PARENT, then committed the fix and confirmed it passes.

Verification:
- `uv run pytest tests/test_hook_frob_suggest.py -p no:cacheprovider -q`:
  26 passed, 0 failed.
- `uv run frob check --only test --ticket T-2908`: 0 errors, 53 warnings
  (all pre-existing, unrelated to this ticket's scope), 5 waived.
- `uv run frob check --land-parity`: 18 unscoped errors, all pre-existing on
  main and unrelated to this ticket's scope (verified by running the same
  command against main directly: COV004/CYCLE001/DOC006/DOC008/TICK004/
  WIRE002 all present there too). Zero COV002/new findings tied to this
  ticket's own diff.
- `uv run frob claude sync --check`: clean after `frob claude sync`
  reconciled the materialized ~/.claude/hooks/frob-suggest.py copy.

### Changed
```
 .claude/hooks/frob-suggest.py      |  48 +++++++++--
 tests/test_hook_frob_suggest.py    | 162 +++++++++++++++++++++++++++++++++++++
 tickets/T-2908/ticket.md           |  35 +++++++-
 tickets/T-2927/ticket.md |  51 ++++++++++++
 4 files changed, 286 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::test_floor_count_stays_quiet_when_grepping_a_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_find_name_still_fires_unscoped_at_repo_root` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_find_name_stays_quiet_when_scoped_to_a_subdirectory` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_raw_worktree_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_raw_worktree_no_longer_recommends_enterworktree` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_hand_edit_ledger_still_fires_on_the_real_ledger` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_hand_edit_ledger_stays_quiet_on_an_unrelated_file` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_recursive_grep_still_fires_unscoped_at_repo_root` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_recursive_grep_stays_quiet_when_scoped_to_a_subdirectory` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_floor_count_still_fires_on_a_genuine_counting_pipeline` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 19 error(s), 515 warning(s), 846 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2908, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
