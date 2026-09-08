---
id: T-4324
title: frob verify status and ticket show hide live rapid-debt.jsonl sweep-deferred
  debt
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/verify_runner.py
- tests/unit/verify/test_verify_runner.py
- docs/modules/verify-rapid-debt-visibility.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: evidence tests and existing frob:doc target this ticket's new symbols reference
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: evidence tests and existing frob:doc target this ticket's new symbols reference
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: avoid unrelated scope-closure expansion; use frob:tests directive instead
    of frob:doc for the new symbol
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: close SCOPE002 doc/test/private-helper closure gaps this file's pre-existing
    directives and this ticket's new test imports require
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: close SCOPE002 doc/test/private-helper closure gaps this file's pre-existing
    directives and this ticket's new test imports require
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/verify/test_watermark.py
  reason: close SCOPE002 doc/test/private-helper closure gaps this file's pre-existing
    directives and this ticket's new test imports require
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'revert: these pre-existing doc/test-target closure gaps predate this ticket
    and are unrelated to its fix; keep scope minimal per ticket instructions'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/verify/_quarantine.py
  reason: 'revert: these pre-existing doc/test-target closure gaps predate this ticket
    and are unrelated to its fix; keep scope minimal per ticket instructions'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/verify-rapid-debt-visibility.md
  reason: new self-contained doc anchor for the new public symbol RapidDebtEntryView
    (COV001/LANDPARITY001)
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/unit/verify/test_watermark.py
  reason: 'revert: this private-helper dependency (test_verify_runner.py -> test_watermark.py::_init_git_repo_with_commits)
    predates this ticket -- the import already existed before any T-4324 edit; adding
    it only cascades into unrelated _watermark.py test-target closure'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: design/frob.strata
  reason: declare the new fs.read call sites (.read_text) this ticket's fix adds in
    verify_runner.py, per SELFAUDIT001
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: design/frob.strata
  reason: 'revert: fixing SELFAUDIT001 there cascades into ~240 unrelated design-doc
    closure obligations; filing as separate pre-existing-debt ticket instead'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: design/frob.strata
  reason: declare the two new fs.read call sites (.read_text) this ticket's fix added
    in verify_runner.py, per SELFAUDIT001 -- land blocks on this as attributable to
    this ticket's own touched file
  actor: logan
  at: '2026-09-08'
evidence:
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_no_baseline_is_live
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_later_baseline_clears
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_uncovered_stays_live
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_other_skip_reasons_are_not_counted
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_clean_status_has_no_live_rapid_debt
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4318 (which is scoped to src/frob/app/ticket_runner/_land_cmd.py
and src/frob/app/ticket_runner/_rapid_sweep.py -- the deferred-sweep budget fix --
and cannot house this fix; the ticket author's own SECOND DEFECT paragraph names
a separate scope: src/frob/app/verify_runner.py and/or src/frob/verify/_watermark.py,
wherever frob verify status's "unverified depth" is computed, plus wherever
rapid-debt.jsonl entries are read back).

MEASURED (2026-09-08): .frob/rapid-debt.jsonl carries 5 live
skipped: post-land-unscoped-sweep-deferred entries (T-4197, T-4301, T-4305,
T-4306, T-4307) that were never cleared or promoted because their deferred
sweep reported UNMEASURABLE (see T-4318). Yet:

- `frob ticket show T-XXXX` for all 5 tickets prints only `[done]`, no
  unverified/debt marker at all.
- `frob verify status` reports "unverified depth (queued land-intents): 0"
  and "quarantine: clear" -- both read clean despite the 5 live debt entries.

An UNMEASURABLE sweep currently reaches nobody outside a log file nobody
reads. A commit that stays unverified needs to be visible wherever a
verified result would be: in `frob ticket show`'s status line, and in
`frob verify status`'s unverified-depth/quarantine summary.

FIX DIRECTION (not dictated): read .frob/rapid-debt.jsonl's live
(uncleared/unpromoted) skipped: post-land-unscoped-sweep-deferred entries
into both surfaces above -- `frob ticket show` should print something
besides a bare `[done]` for a ticket with a live debt entry, and
`frob verify status`'s "unverified depth" count should include them.

T-4318 partially addresses the root cause (the deferred sweep's --budget
truncation) by passing full=True to _unscoped_error_findings for the
detached sweep child, which should sharply reduce how often this debt is
created going forward -- but does not fix the status-visibility gap for
debt that is created (whether by a genuinely wedged full check, a refused
spawn, or historical entries already in rapid-debt.jsonl).