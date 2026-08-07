---
id: T-1762
title: Every --force override discharges a safety obligation with no reason and no
  audit trail; audit the whole flag family
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_archive.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- tests/test_tickets_organization.py
- src/frob/tickets/_force_override.py
- src/frob/_cli_parsers/_ticket/_progress.py
- docs/modules/tickets.md
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_archive.py
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_land_finish_guard.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_force_override.py
  reason: 'Re-adding scope lost in the v2 ledger migration merge (main''s

    tickets/T-1762/ticket.md reset scope to the original 4-file brief).

    This file houses the shared force-override audit primitive

    (ForceOverrideEntry/record_force_override) both --force call sites use.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: 'Re-adding scope lost in the v2 ledger migration merge: land --finish

    --force''s CLI parser wiring (--reason/--reason-file flags) lives in

    _progress.py, not _closeout.py (which only wires archive --force).

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: 'docs/modules/tickets.md houses the new ForceOverrideEntry data model

    and the "--force audit trail (T-1762)" section documenting the

    mandatory-reason/audit-record shape -- re-adding after the v2 ledger

    migration merge reset scope to the original brief.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/config.py
  reason: 'Re-adding scope lost in the v2 ledger migration merge: --force''s new

    ticket_force_reason/ticket_force_reason_file AppConfig fields and the

    _archive/__init__.py dispatch-lambda wiring that threads cfg into

    _archive''s new kwargs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'Re-adding scope lost in the v2 ledger migration merge: --force''s new

    ticket_force_reason/ticket_force_reason_file AppConfig fields and the

    _archive/__init__.py dispatch-lambda wiring that threads cfg into

    _archive''s new kwargs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_archive.py
  reason: 'Re-adding scope lost in the v2 ledger migration merge: --force''s new

    ticket_force_reason/ticket_force_reason_file AppConfig fields and the

    _archive/__init__.py dispatch-lambda wiring that threads cfg into

    _archive''s new kwargs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'Re-adding scope lost in the v2 ledger migration merge: --force''s new

    ticket_force_reason/ticket_force_reason_file AppConfig fields and the

    _archive/__init__.py dispatch-lambda wiring that threads cfg into

    _archive''s new kwargs.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_land_finish_guard.py
  reason: 'Re-adding scope lost in the v2 ledger migration merge: the pre-existing

    test _finish_worktree(..., force=True) call needed force_reason= to

    keep passing under the new reason-required contract; two new tests

    live here too.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'design/frob.strata declares the fs.write/fs.read capabilities for the

    new force-overrides.jsonl write site and the new test file, plus the

    ForceOverrideError/record_force_override interface= entries

    (frob sys sync-interface) -- required to clear SELFAUDIT001 SYS100/

    SYS104 findings T-1762''s own new code introduces. SCOPE002''s resulting

    cascade is warnings-only (confirmed empirically), not a blocking gate;

    narrower per-symbol scoping does not exist for ticket scope (file

    globs only).

    '
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_tickets_organization.py::TestForceOverrideAudit::test_record_force_override_requires_reason
- tests/test_tickets_organization.py::TestForceOverrideAudit::test_record_force_override_appends_a_line
- tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_no_live_lease_needs_no_reason
- tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_live_lease_and_no_reason_refuses
- tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_force_removes_despite_a_live_process
- tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_finish_worktree_force_requires_reason_when_guard_would_fire
- tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_finish_worktree_force_is_a_no_op_reason_wise_when_worktree_is_free
designated_repro_test: null
threat: null
component: null
---
`--force` overrides discharge real safety obligations with NO reason, NO
log line, and NO audit entry. Two confirmed instances, found by a
deliberate search for the T-1733 shape (a flag that discharges an
obligation more cheaply than the honest route):

1. **`frob ticket archive --force`** (`frob.tickets._archive.archive`)
   skips `_refuse_archive_if_leased`, the T-0843 live-cross-worktree-lease
   guard, entirely. That guard exists because skipping it once already
   caused a field incident (T-0753, cited in the guard's own docstring).
   The override that bypasses it costs nothing to invoke and leaves no
   trace that it was invoked.

2. **`frob ticket land --finish --force`**
   (`_land_cmd._finish_worktree`, called as
   `_finish_worktree(root, worktree, cfg.ticket_id, force=cfg.ticket_force)`)
   skips `_refuse_finish_if_worktree_in_use` -- the T-1715 liveness guard
   that stops a worktree being deleted out from under a live process.
   Same silence, higher stakes: this one removes a checkout outright.

THE SECOND ONE WAS INTRODUCED TODAY, BY THE COORDINATOR, IN THE VERY
TICKET THAT ADDED THE GUARD. T-1715's brief said "`--force` may override
for a genuinely wedged tree" and said nothing about recording why. So a
guard was added to prevent an irreversible deletion, and in the same
change an unaccountable bypass for it was specified. That is the exact
pattern T-1733 had established hours earlier -- and it was reintroduced
by the person who had been citing T-1733 all day. A principle that lives
only in prose gets re-violated by its own author.

THE RULE, which should be applied as a rule rather than instance by
instance: **every way to discharge an obligation cheaply must cost at
least as much bookkeeping as the honest way.** `frob ticket scope`
already requires `--reason`. `frob ticket evidence --replace` now does
(T-1733). `frob ack` now does (T-1317). `--force` is the remaining
family.

REQUIRED:

1. `--force` on `archive` and on `land --finish` requires
   `--reason`/`--reason-file`, refusing without one, exactly as `scope`
   and `evidence --replace` do.
2. Every forced bypass appends an append-only audit record naming the
   guard bypassed, the reason, the actor, and the target -- reusing the
   established `ScopeChangeEntry`/`AcceptanceAmendmentEntry`/
   `EvidenceChangeEntry`/`AckAuditEntry` shape rather than inventing a
   fifth.
3. Every forced bypass logs at WARNING naming the guard it skipped. A
   bypass nobody can see is indistinguishable from the guard not existing.
4. AUDIT THE WHOLE FAMILY, do not fix only these two. Enumerate every
   `--force`/`--skip`/`--override`/`--bypass` flag from the CLI parsers
   (from the parser definitions, NOT a hand-written list -- a hand list
   is the same defect class as the bug) and classify each as either
   "discharges a tracked safety obligation" or "narrows one invocation
   without clearing a finding". The first class needs a reason; the
   second does not. `frob check --skip-*` is the second class and is
   correctly free: the finding re-fires next run.

   Report the classification table in the Done report. That table, not
   the two fixes, is the deliverable -- it is what makes the rule
   enforceable for flags added later.
5. Consider a gate rule that fails when a new CLI flag matching the
   override shape is added without a paired reason argument, so flag
   number nine cannot repeat this. If that is cheap, do it; if it needs
   guesswork, say so and stop at the audit.

Credit: found by the T-1317 agent, which went looking for this shape
specifically after being briefed on T-1733 and reported that it stopped
at two only after a systematic search turned up no third.