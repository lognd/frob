---
id: T-2902
title: 'post-land sweep regression from T-2891, T-1604: 5 new (rule, file) identit(ies),
  5 finding(s) (DOC006, DOC008, LANG003)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/commands/check.md
- docs/modules/gates.md
- src/frob/lang (facet=capability)
- src/frob/lang (facet=docblock)
- src/frob/lang (facet=dup)
findings:
- - DOC006
  - docs/modules/gates.md
- - DOC008
  - docs/commands/check.md
- - LANG003
  - src/frob/lang (facet=capability)
- - LANG003
  - src/frob/lang (facet=docblock)
- - LANG003
  - src/frob/lang (facet=dup)
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: measurement, fix summary, BUG002 waiver for doc-only fix
  actor: logan
  at: '2026-08-26'
  old_length: 2377
  new_length: 4473
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2891, T-1604 at commit e0431cc1de01133d6afce563695bf510fd43a3fb found 5 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (5), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 5 actual finding(s) across those 5 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  docs/modules/gates.md
- DOC008  docs/commands/check.md
- LANG003  src/frob/lang (facet=capability)
- LANG003  src/frob/lang (facet=docblock)
- LANG003  src/frob/lang (facet=dup)

T-2009: 2 lands (T-2891, T-1604) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2891, T-1604 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  docs/modules/gates.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC008  docs/commands/check.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG003  src/frob/lang (facet=capability)  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG003  src/frob/lang (facet=docblock)  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG003  src/frob/lang (facet=dup)  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

Measured on current main (worktree HEAD, merged from main) via `frob
check --only docblocks` (DOC006/gates.md), `frob check --only doclink
--only docanchor` (DOC008/check.md), and `frob check --only
lang_project_conformance` (LANG003 x3).

DOC006 docs/modules/gates.md: reproduces -- an inline backtick-quoted
anchor reference to `docs/commands/check.md#tool-summary-pass--fail--
unres-t-2891` was split across a hard line wrap in the markdown source
(the anchor slug broke across two lines, producing a stray embedded
space that does not match any real heading). FIXED: reflowed so the
whole backtick span stays on one source line.

DOC008 docs/commands/check.md: reproduces -- `[UNRESOLVED](gates.md#unresolved-t-1664)`
resolves relative to docs/commands/, but the real file is
docs/modules/gates.md. FIXED: corrected the relative path to
`../modules/gates.md#unresolved-t-1664` (anchor itself was always
correct -- `## Unresolved (T-1664)` in docs/modules/gates.md slugs to
`unresolved-t-1664`).

LANG003 src/frob/lang (facet=capability, facet=docblock, facet=dup):
do NOT reproduce on current main. `frob check --only
lang_project_conformance` today reports LANG003 only for facet=arch
(bash/c/csharp/rust/typescript, T-0329, unrelated to this ticket).
T-2906 ("wire bash+csharp into frob.vet/frob.dup/frob.gates._docblocks
(capability/dup/docblock facets)", commit 0163ae2cf, landed 2026-08-25
22:07:25) landed AFTER T-2902's blamed commit (e0431cc1,
2026-08-25 19:25:38) and directly implements the capability/dup/
docblock facets these 3 findings were about -- they are stale,
already-fixed residue from before T-2906 landed, not a currently-live
regression.

frob:waive BUG002 reason="the DOC006/DOC008 fixes here are markdown formatting/link corrections with no code behavior change; there is no production code path to reproduce with a failing-at-parent test. Bound evidence (TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass) demonstrates the doclink_gate mechanism this fix relies on and is necessarily confirmatory, same as T-2893's BUG002 waiver for the same reason"
