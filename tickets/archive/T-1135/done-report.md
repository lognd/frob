## Done report

: T-1135 EPIC frob refactor: transactional move/rename/split with full
reference, directive, and obligation rewrite

Single child T-1197 (reference-rewrite engine) is done in
`tickets/archive/`, and re-verification found the code covers all three
acceptance criteria directly, not just via T-1197's own narrower
acceptance text:

- `src/frob/refactor/_alias_policy.py` -- alias-conflict policy
  (auto-generated import alias on destination/call-site name collision).
- `src/frob/refactor/_apply.py` -- AST-level move/rewrite with
  overlapping-op refusal before any write
  (`_find_overlapping_ops`/`test_overlapping_ops_refuse_before_write`).
- `src/frob/refactor/_transaction.py` -- the resolve/plan/apply/verify
  pipeline with `git reset --hard` rollback on any verify failure, never
  touching `refs/stash`.
- `src/frob/refactor/_verify.py` -- `verify_import_resolution` (real
  import-graph resolution for absolute repo-owned imports, disclosed
  scope), `verify_pytest_collect`, `verify_check_delta` (invokes
  `sys.executable -m frob check --delta`, not a possibly-stale global
  binary, per agent-playbook.md sec 2).
- `src/frob/refactor/_directives.py` -- `frob:` comment-DSL directive
  carrier rewrite (frob:tests/frob:doc/frob:enforces target forms,
  waiver symrefs including `path::` prefixes).
- `src/frob/refactor/_repointer.py` -- PII012 allowlist re-keying,
  check-coverage registry citation rewrite, archived-ticket evidence
  node-id repointing (both monofile-era and per-ticket-ledger-file
  forms).
- `src/frob/refactor/_prose.py` -- docstring/comment dotted-path
  rewrite, docs/** prose and code-block rewrite, doc-anchor heading-slug
  rewrite.
- `src/frob/refactor/_split.py` -- the split verb (T-1072/T-1077
  family-extraction pattern).

All three acceptance criteria were UNBOUND on this ticket even though
T-1197 (its only child) is done -- the epic's own criteria are worded
more broadly than T-1197's ("frob-owned reference... in the widest
sense: frob:tests/frob:doc/frob:enforces, waiver symrefs, PII012, registry
citations, evidence node ids; every prose mention including frob:
directive targets anywhere in the repo, docs/** anchors"). Re-verifying
against the actual `_repointer.py`/`_directives.py`/`_prose.py` code
(not present when T-1197 alone was reviewed -- these came from later,
uncredited follow-on work under the same T-1135 umbrella that never got
its own child ticket) confirmed the code satisfies the epic's own wider
wording, not just T-1197's narrower one. No amendment was needed: the
criteria's text matches what shipped.

## Acceptance

- [0] full reference/directive/obligation rewrite (imports, aliasing,
  frob:tests/frob:doc/frob:enforces, waiver symrefs incl. path::,
  PII012, registry citations, archived evidence node ids): bound to
  `tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision`,
  `tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten`,
  `tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move`,
  `tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten`,
  `tests/test_refactor.py::TestRepointer::test_archived_per_ticket_ledger_file_evidence_rewritten`
- [1] refuse-and-rollback on an incomplete rewrite, verified in-command:
  bound to
  `tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree`,
  `tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write`
- [2] prose/docstring/comment rewrite incl. frob: directive targets and
  doc anchors: bound to
  `tests/test_refactor.py::TestProseCarrier::test_docs_prose_and_code_block_rewritten`,
  `tests/test_refactor.py::TestRunRefactor::test_run_refactor_does_not_roll_back_on_ticket_md_evidence_carrier`

All 9 re-run fresh this session:
`pytest <the 9 node ids above> -p no:cacheprovider -q` ->
`SUITE-RESULT: exitstatus=0 collected=9 failed=0`.

## Filed

None -- no residue found. Multi-language binding tables (TS/Rust/C-C++/
Kotlin) are explicitly out of scope per the ticket's own body ("Python
first... extend it later") -- not a gap in this closure.

## Cuts

None disclosed as outstanding.

### Changed
(no changed files detected -- this ticket only closes an already-shipped
epic)

### Evidence
- `tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision`
- `tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten`
- `tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move`
- `tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten`
- `tests/test_refactor.py::TestRepointer::test_archived_per_ticket_ledger_file_evidence_rewritten`
- `tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree`
- `tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write`
- `tests/test_refactor.py::TestProseCarrier::test_docs_prose_and_code_block_rewritten`
- `tests/test_refactor.py::TestRunRefactor::test_run_refactor_does_not_roll_back_on_ticket_md_evidence_carrier`

### Changed
```
 tickets/T-1135/ticket.md      | 31 ++++++++++++--
 tickets/T-1137/done-report.md | 97 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1137/ticket.md      | 35 +++++++++++++---
 tickets/T-1219/done-report.md | 88 +++++++++++++++++++++++++++++++++++++++
 tickets/T-1219/ticket.md      | 23 +++++++++-
 tickets/T-2468/ticket.md      |  2 +-
 6 files changed, 265 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRepointer::test_archived_per_ticket_ledger_file_evidence_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestProseCarrier::test_docs_prose_and_code_block_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunRefactor::test_run_refactor_does_not_roll_back_on_ticket_md_evidence_carrier` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-1135/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py


frob:no-behavior-change reason="epic-rollup close: T-1135's only child T-1197 is shipped and archived done; re-verification confirmed the code (refactor/_repointer.py, _directives.py, _prose.py, _alias_policy.py, _transaction.py) satisfies the epic's own wider acceptance wording, no amendment or code change needed"
