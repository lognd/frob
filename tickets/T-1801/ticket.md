---
id: T-1801
title: Fix ARCH103/SEC110 in _resolve_ticket_root (T-1674 land introduced)
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_app_runners_batch7.py
- rapid-debt.jsonl
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
- tickets/T-1796/done-report.md
- tickets/T-1801/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: test coverage for the split root-resolution helpers lives beside TestTicketRunnerRootResolution
    in this file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: rapid-debt.jsonl
  reason: carried on this same branch from T-1796's own land (not touched by this
    ticket's own code); tickets/T-1801/ticket.md is this ticket's own v2
    ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: carried on this same branch from T-1796's own land (not touched by this
    ticket's own code); tickets/T-1801/ticket.md is this ticket's own v2
    ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: carried on this same branch from T-1796's own land (not touched by this
    ticket's own code); tickets/T-1801/ticket.md is this ticket's own v2
    ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1796/done-report.md
  reason: carried on this same branch from T-1796's own land (not touched by this
    ticket's own code); tickets/T-1801/ticket.md is this ticket's own v2
    ledger file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1801/ticket.md
  reason: carried on this same branch from T-1796's own land (not touched by this
    ticket's own code); tickets/T-1801/ticket.md is this ticket's own v2
    ledger file
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_frob_root_env_used_when_path_not_explicit
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_explicit_path_wins_over_frob_root
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_no_frob_root_falls_back_to_cwd_default
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_resolved_root_is_logged_for_a_mutating_verb
designated_repro_test: null
threat: null
component: null
---
T-1674's own land introduced two gate findings against
`_resolve_ticket_root` (`src/frob/app/ticket_runner/__init__.py`):

ARCH103: the function mixes I/O, string-formatting, and 4 decision
points in one body -- split into separable questions (explicit --path
wins outright; the "." sentinel means unset; the FROB_ROOT env fallback;
the final cwd default).

SEC110: reads os.environ.get("FROB_ROOT") -- an env-var read is a
secret-source observation gate; FROB_ROOT carries a filesystem path,
never a credential, so a frob:waive SEC110 is the correct resolution
here (not a new std.secrets node), with a reason describing WHY this
variable cannot carry a secret.

Also: correct the docstring's claim that "a coordinator's dispatch
wrapper already pins its measurement root by hand for exactly this
reason" -- that was not accurate; reword to describe the INTENT
(FROB_ROOT is the mechanism that lets a coordinator stop relying on
ambient cwd), not an existing practice.