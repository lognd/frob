---
id: T-2647
title: unused _LEDGER_TRANSACTIONAL_VERBS import raises quarantine and forces synchronous
  lands fleet-wide
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py
  reason: 'T-2647: new F401 repro test binding the __all__ fix to a genuine before/after
    failure'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared::test_ticket_runner_init_has_no_f401_finding
- tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared::test_ledger_transactional_verbs_still_importable_from_ticket_runner
designated_repro_test: tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared::test_ticket_runner_init_has_no_f401_finding
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

    ruff check --select F401 src/frob/app/ticket_runner/__init__.py
    -> Found 1 error: unused import `_LEDGER_TRANSACTIONAL_VERBS`

Real, and it raised quarantine -- which turns OFF deferred landing
repo-wide and forces every agent's land into fully-synchronous
verification (T-1693).

## Cause

T-2603 unified the ledger-write verb classification into a single table
with a declared per-verb strategy, and made `_LEDGER_TRANSACTIONAL_VERBS`
and `MIRRORED_LEDGER_VERBS` derived aliases rather than independently
declared sets. The import in `ticket_runner/__init__.py` survived the
change with no remaining consumer.

## Attribution note (not this ticket's fix)

Quarantine blamed batch `c4880b01` (T-2580's land). `git show --stat` on
that commit shows 9 files changed and NONE under `ticket_runner/`. So the
finding is real but the attributed land did not cause it -- the same
misattribution class already tracked by T-2571/T-2595 and the third variant
noted in T-2596. Do not re-file that here; just do not trust the blame line.

## Fix

Either remove the import, or add `_LEDGER_TRANSACTIONAL_VERBS` to `__all__`
if it is intended as a re-export for other modules. Determine which by
checking for real consumers -- `uv run frob explore xref
_LEDGER_TRANSACTIONAL_VERBS` reports the definition and every use site.

If it IS a deliberate re-export, `__all__` is the correct declaration and
makes the intent explicit rather than leaving a bare import that reads as
dead. If nothing consumes it, delete it.

## Positive controls, both directions

- `ruff check --select F401` on that file is clean afterward
- every existing consumer of `_LEDGER_TRANSACTIONAL_VERBS` and
  `MIRRORED_LEDGER_VERBS` still resolves and behaves identically -- T-2603
  made these derived aliases, so a careless removal could break the
  compatibility surface it deliberately preserved
- `frob verify status` shows quarantine clear