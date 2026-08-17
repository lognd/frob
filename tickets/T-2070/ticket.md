---
id: T-2070
title: 'post-land sweep regression from T-1959, T-2003, T-2016: 3 new (rule, file)
  identit(ies), 2 finding(s) (COV001, DOC002, DSL001)'
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/strata/_claims.py
- docs/strata/kernel.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/kernel.md
  reason: DOC002 fix requires writing the missing claim-evaluation section this ticket's
    frob:doc anchor points at
  actor: logan
  at: '2026-08-10'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-1959, T-2003, T-2016 at commit 093254241378b66abf0d434bb21760da596be2b4 found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (3), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 3 identit(ies).

New (rule, file) identit(ies) filed here:

- COV001  src/frob/strata/_claims.py
- DOC002  src/frob/strata/_claims.py
- DSL001  src/frob/app/ticket_runner/_query.py

T-2009: 3 lands (T-1959, T-2003, T-2016) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-1959 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/strata/_claims.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/strata/_claims.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DSL001  src/frob/app/ticket_runner/_query.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Done report

frob:no-behavior-change reason="docs-only fix for T-2070: writes the missing docs/strata/kernel.md#claim-evaluation section that evaluate_claims's own frob:doc directive already promised; does not touch evaluate_claims's implementation or any other runtime code path. The bound evidence test is a CLI-dispatch integration test unrelated to strata's claim evaluation and correctly PASSES at both main and this ticket's own HEAD, which is exactly what a genuine no-behavior-change claim requires."

## Done report

Changed:
- docs/strata/kernel.md (new section "## Claim evaluation", frob:doc target for evaluate_claims)
- tickets/T-2070/ticket.md (scope extended to include docs/strata/kernel.md; evidence bound; via frob ticket CLI)

Root cause: the frob:doc directive at src/frob/strata/_claims.py:719 pointed at
docs/strata/kernel.md#claim-evaluation, but no heading of that slug existed in
kernel.md (confirmed against main: only "## Claim forms and their decision
procedures" existed, not "## Claim evaluation"). DOC002 correctly flagged the
unresolved anchor; because an unresolved frob:doc edge does not count toward
coverage, COV001 then reported evaluate_claims as having no doc edge at all.
One defect, two findings, as the brief predicted.

Fix chosen: candidate (b) -- wrote the missing documentation rather than
retargeting the anchor to an existing section. No existing kernel.md section
documents evaluate_claims's own contract (order-preserving, fail-closed,
cascade-downgrade delegation to evidence.md#the-enables-cascade); "Claim
forms and their decision procedures" documents the per-claim-form procedures
table, not the whole-model entrypoint, so retargeting there would have been
inaccurate. The new section also carries a frob:describes directive so the
doc graph itself now records the edge, and cross-references "Verdict report"
and evidence.md rather than duplicating their content.

DSL001 (src/frob/app/ticket_runner/_query.py) re-measured and does NOT
reproduce: checked every --only stage group that can run gate:WAIVE's
directive validation (gates-fast, gates-security, gates-native, static,
lint) plus a manual read of every frob: directive in _query.py -- all
well-formed. T-2070's ticket body itself only lists 2 actual findings
across the 3 (rule, file) identities and says the third may be
"pre-existing residue the rolling baseline simply had not recorded yet";
that is what this measurement confirms for DSL001 specifically -- either
already-fixed or never real against the measured commit.

Evidence: docs-only ticket, no pytest surface of its own. Per playbook
section 5's precedent, recorded the existing CLI-dispatch integration test:
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

Measured (worktree tree, post-merge with main):
- `timeout 540 uv run frob check --only coverage --json`: 0 COV001 for
  src/frob/strata/_claims.py (grep-verified against the full JSON output;
  the only _claims.py hits left are pre-existing waived COV007s unrelated
  to evaluate_claims).
- `timeout 540 uv run frob check --only docanchor --json`: 0 DOC002 findings
  repo-wide (grep-verified: zero occurrences of the string "DOC002" in the
  output).
- `timeout 540 uv run frob check --only gates-fast --ticket T-2070 --json`:
  0 errors (after `frob ticket scope T-2070 --add docs/strata/kernel.md`
  and a fresh `frob ticket sweep T-2070` to clear a stale-prework PRE001).
- `timeout 540 uv run frob check --land-parity` (after merging main which
  includes T-2077's ARCH001 fix for _rapid_sweep.py): clean, 0 unscoped
  error(s) repo-wide.
- `git diff main --diff-filter=D --stat`: empty (no unintended deletions).

Filed: none.

Gates: frob check --land-parity clean repo-wide (0 unscoped errors) after
merging main.

### Changed
```
 docs/strata/kernel.md         | 21 +++++++++++
 tickets/T-2070/done-report.md | 87 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2070/ticket.md      | 14 ++++++-
 3 files changed, 121 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)
