## Done report

mirror_promote_to_primary (src/frob/app/ticket_runner/_ledger_mirror.py)
mirrors ONLY the ledger half of a `frob ticket promote` rename onto the
primary checkout: it reads back `_commit_promote_rename`'s deterministic
commit subject to recover `final_id` (never importing
`_draft_finalize`'s private call chain, since that file is outside this
ticket's declared scope), copies `final_id`'s `_ledger_pathspecs` onto
`primary`, and removes `draft_id`'s vacated v2 directory there if one
happens to exist. It is deliberately NOT added to `MIRRORED_LEDGER_VERBS`
-- promote's write is a multi-file rename (renumber_one rewrites code
references across the tracked tree), not the single ticket-pathspec
shape that set assumes, and mirroring the full rename the same
pathspec-limited way would risk carrying a dirty worktree's unrelated
uncommitted source edits onto main. `_auto_commit_ledger_after_dispatch`
(src/frob/app/ticket_runner/__init__.py) calls it directly as a
`"promote"` special case, ahead of the pre-existing
`_LEDGER_TRANSACTIONAL_VERBS` early return.

`_mirror_target` was split into a shared `_resolve_mirror_primary` (no
`MIRRORED_LEDGER_VERBS` membership check) plus the original
membership-gated wrapper, so `mirror_promote_to_primary` can reuse the
same primary-resolution/land-guard logic.

Judgment on unifying `_LEDGER_TRANSACTIONAL_VERBS` and
`MIRRORED_LEDGER_VERBS`: I looked at this and did NOT unify them.
`_LEDGER_TRANSACTIONAL_VERBS` answers "does this verb own its own commit
sequence" (orthogonal to mirroring); `MIRRORED_LEDGER_VERBS` answers
"is this verb's write a single ticket-pathspec copy". `promote` is a
member of the first and needs a THIRD write pattern the second set's
copy-the-declared-pathspec shape does not fit (read-back-final-id-from-
commit-message, copy the new location, delete the old one). Folding a
structurally different pattern into either existing table to avoid "two
lists" would just move the duplication into a table whose entries mean
different things per key -- the same shape of bug T-2197/this ticket
already paid for once. A real fix is a single verb table with an
explicit per-verb mirror-strategy attribute (own-commit: yes/no,
mirror-strategy: none/pathspec-copy/rename-readback/...), covering every
current member of both sets, not a promote-shaped patch on the smaller
one. That is real design work spanning both modules' full membership,
not a T-2587-sized change -- documented in
docs/modules/tickets-lifecycle.md's new "promote gets its own dedicated
mirror" section, and left as a judgment call for a future ticket rather
than filed reflexively, since no other verb currently needs a third
pattern.

Also touched (all within this ticket's own scope, added via `frob ticket
scope --add` with reasons recorded on the ticket): design/frob.strata
(new `fs.write` capability declaration for the `shutil.rmtree` call) and
docs/modules/tickets-lifecycle.md (the AFFECT001-required doc anchor
update, which also documents the two-tables judgment above).

Residual, not fixed here (pre-existing, unrelated to this diff, verified
via a clean parent-commit comparison and via the fix commit containing
no changes under src/frob/strata|core|gates|graphlang|testsuite): repo
still carries the T-1929/T-2025-adjacent unscoped SELFAUDIT001 ratchet
violations reported by `tests/system/test_frob_self_model.py::
TestFrobSelfModel::test_sys_gate_zero_violations` (core fs.read,
gates exec, graphlang env.read/fs.read, testsuite env.read/env.write
ratchet-ceiling growth, plus a testsuite env.read via-list gap at
tests/test_coverage.py:854). None of it is under this ticket's scope or
touched by this diff; no follow-up filed since it is pre-existing repo
floor, not a regression this ticket introduced.

### Changed
```
 design/frob.strata                             |   7 +-
 docs/modules/tickets-lifecycle.md              |  49 ++++++++
 src/frob/app/ticket_runner/__init__.py         |  20 ++-
 src/frob/app/ticket_runner/_ledger_mirror.py   | 168 ++++++++++++++++++++++---
 tests/unit/test_ticket_runner_ledger_mirror.py | 161 +++++++++++++++++++++++-
 tickets/T-2587/ticket.md                       |   8 +-
 6 files changed, 390 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror::test_promote_from_worktree_is_visible_on_primary_without_a_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror::test_promote_mirror_does_not_leak_source_changes_or_duplicate_the_draft` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror::test_worktree_merging_main_afterward_does_not_conflict_on_the_ticket_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror::test_head_not_a_promote_commit_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror::test_running_in_the_primary_checkout_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH102@src/frob/tickets/_doable.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2587/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
