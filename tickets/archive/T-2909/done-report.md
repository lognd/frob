## Done report

Split docs/guides/agent-playbook.md into a hot-path checklist plus
docs/guides/agent-playbook-appendix.md.

Before/after (measured directly):

- Before: docs/guides/agent-playbook.md = 1446 lines / 86013 bytes
  (single file).
- After:
  - docs/guides/agent-playbook.md (hot path) = 530 lines / 28236 bytes --
    a 63% line reduction / 67% byte reduction from the original.
  - docs/guides/agent-playbook-appendix.md (full narrative record) =
    1455 lines / 86668 bytes (slightly larger than the original due to the
    new intro paragraph explaining the split; every original section is
    otherwise preserved verbatim, including all headings/anchors).

Approach: the appendix is the ORIGINAL file content (all sections,
incidents, and measurements) with only the intro paragraph rewritten to
point back at the hot-path file -- this guarantees nothing was lost by
construction rather than by careful transcription. The hot-path file is a
new, concise rewrite that keeps every RULE an agent must obey in the
moment (the full section 0 dispatch contract, the worktree warm-up
checklist, the mid-ticket discipline, the land ritual) and replaces each
narrative/incident passage with a one- or two-sentence summary plus an
explicit pointer to the corresponding appendix section by heading anchor.
Sections moved to the appendix ENTIRELY (heading no longer appears in the
hot-path file): 1b2 (conflicted stash-pop index hazard), 3b's full
chunking/measurement detail (compact recipe kept in hot path), 6d/6e/6f
(TEST005 coverage-artifact archaeology), 10b (ledger v1 monofile finalize
recipe, largely superseded by ledger v2 anyway), and 13 (the land-cost
design finding -- the one directly actionable step inside it,
`wait_for_land_slot.py`, was promoted into the hot-path section 0 land
ritual instead of being dropped). Sections kept in the hot path with their
original heading text/anchor unchanged, narrative trimmed: 1, 1b, 1c, 1d,
4c, 6, 10, 12b.

Reference audit (`git grep -n "agent-playbook"` across the whole tree,
including archived tickets):

- The ONLY structured `frob:doc` graph edge naming a playbook anchor is
  `src/frob/tickets/_worktree_sweep.py:181` -> `#12b-...` -- section 12b's
  heading text is unchanged in the new hot-path file, so this edge still
  resolves; no code change needed.
- Twelve distinct `#anchor` references were found across docs/tests/src
  (see the ticket's own audit). Eleven point at sections that KEPT their
  original heading in the hot-path file (1, 1b, 6, 6c, 6g, 10,
  10-ledger-conflict-splice-guidance, 11b, 12b) and therefore still
  resolve unchanged. The one exception --
  `docs/audits/test005-zero-classification-t1418.md:9`, pointing at
  section 6d (moved fully to the appendix) -- was updated to point at
  `docs/guides/agent-playbook-appendix.md#6d-...` instead.
- `.claude/hooks/sync-claude-config.py`'s `MANAGED` list materializes
  `docs/guides/agent-playbook.md` to `~/.claude/refs/agent-playbook.md`
  (T-1808). No code change needed (the mapping still points at the same
  source path, now shorter); ran `frob claude sync` to reconcile the
  drifted materialized copy after editing the source, confirmed via
  `frob claude sync --check` -- "9 file(s) in sync".
- No other tracked reference needed a code change: all other hits were
  either archived tickets/done-reports (historical record, never edited),
  or prose mentions of "agent-playbook.md" with no anchor that still
  correctly name the (still-existing, still-canonical) hot-path file.

New-file plumbing: added `docs/guides/agent-playbook-appendix.md` to
`docs/index.md`'s guide list as a second, genuine inbound reference
(REF002 flagged the new file as having only one inbound reference before
this -- the pointer from agent-playbook.md itself -- matching the existing
convention other singly-anchored docs use of indexing from `docs/index.md`
rather than waiving).

Verification:
- `uv run frob check --only doclink --only docanchor --ticket T-2909`:
  0 errors tied to this ticket (one pre-existing, unrelated DOC008 in
  docs/commands/check.md, confirmed present on main too).
- `uv run frob check --only refs`: gate:REF 0 errors (REF002 on the new
  appendix file resolved by the docs/index.md addition).
- `uv run frob check --land-parity`: 19 unscoped errors, all pre-existing
  on main and unrelated to this ticket's scope (COV004 attachment-sha
  drift on other tickets, CYCLE001, DOC006/DOC008 on unrelated docs,
  TICK004, WIRE002 -- verified by running the identical command against
  main directly and finding the same set).
- `uv run frob claude sync --check`: "9 file(s) in sync" after
  `frob claude sync` reconciled the materialized ~/.claude/refs copy.
- Evidence: docs-only ticket with no pytest surface of its own, per the
  playbook's own T-0167 precedent -- recorded
  tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches,
  observed passing (`SUITE-RESULT: exitstatus=0 collected=1 failed=0`).

### Changed
```
 docs/audits/test005-zero-classification-t1418.md |    2 +-
 docs/guides/agent-playbook-appendix.md           | 1455 +++++++++++++++++++++
 docs/guides/agent-playbook.md                    | 1520 +++++-----------------
 docs/index.md                                    |    5 +
 tickets/T-2909/ticket.md                         |   92 +-
 5 files changed, 1854 insertions(+), 1220 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 20 error(s), 451 warning(s), 847 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC006@tickets/T-2923/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2909, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
