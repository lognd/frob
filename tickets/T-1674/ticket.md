---
id: T-1674
title: 'Every frob verb resolves root from cwd silently: widen T-1638 beyond land'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/config.py
- tests/unit/test_app_runners_batch7.py
- design/frob.strata
- rapid-debt.jsonl
- src/frob/app/ticket_runner/_lifecycle.py
- tests/test_ticket_work_and_land_finish.py
- tickets/T-1674/ticket.md
- tickets/T-1786/ticket.md
- tickets/T-1790/done-report.md
- tickets/T-1795/ticket.md
- tickets/T-1796/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'narrowing from the unscoped ticket: this pass covers item 1 (report the
    resolved root, unconditionally) and the FROB_ROOT half of item 2 (--path already
    exists as the override) for the frob ticket <verb> dispatch choke point only --
    item 3 (per-verb ownership refusal) explicitly overlaps T-1669 per the ticket''s
    own body and is left there; widening to every OTHER frob subcommand family (not
    just frob ticket) is a natural follow-up, not done in this pass'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/config.py
  reason: 'narrowing from the unscoped ticket: this pass covers item 1 (report the
    resolved root, unconditionally) and the FROB_ROOT half of item 2 (--path already
    exists as the override) for the frob ticket <verb> dispatch choke point only --
    item 3 (per-verb ownership refusal) explicitly overlaps T-1669 per the ticket''s
    own body and is left there; widening to every OTHER frob subcommand family (not
    just frob ticket) is a natural follow-up, not done in this pass'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: new tests for _resolve_ticket_root/root-resolution logging belong beside
    the existing TestTicketRunnerDispatch class in this file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: rapid-debt.jsonl
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1674/ticket.md
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1786/ticket.md
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1790/done-report.md
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1795/ticket.md
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1796/ticket.md
  reason: design/frob.strata for SELFAUDIT001/SYS100/SYS104 (env.read capability +
    interface declaration for the new os.environ.get call and _resolve_ticket_root);
    rapid-debt.jsonl/_lifecycle.py/test_ticket_work_and_land_finish.py/ticket ledger
    files carried on this same branch from T-1790's own land plus this worktree's
    earlier ticket-management ops, not touched by T-1674's own code
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
T-1638 records that 'frob ticket land' resolves the repo root from cwd, so running it from inside a worktree targets the wrong tree. The defect is not specific to land -- it is how EVERY frob verb resolves root, and the ledger-writing verbs are just as damaging.

Field incident, coordinator, 2026-08-06: a shell whose cwd had drifted into .claude/worktrees/w34-dispatch ran 'frob ticket new'. The ticket was filed into that WORKTREE's ledger rather than main's, and nothing in the output said so -- the command printed a created id and exited 0, identical to a correct run. It was caught only because the id came back as a T-draft-* rather than a T-#### (drafts are allocated in worktrees), and that tell exists only for 'new'. 'close', 'drop', 'evidence', and 'done-report' would have written to the wrong ledger with no distinguishing signal at all. In this case the worktree was about to land, so promotion recovers it; had the worktree been abandoned, the ticket would have been silently destroyed.

This is the R4 shape (position validated too late) and the same class as the earlier incident where a gate measurement was taken against a worktree and reported as main's number.

Work:
1. Every frob command reports the root it resolved -- at minimum on any ledger-writing or measuring verb, unconditionally, not behind -v. A run that cannot be attributed to a tree is not a trustworthy run.
2. Add an explicit --root / FROB_ROOT override so a caller can pin the tree rather than depending on ambient cwd. The coordinator's own measure wrapper already pins ROOT by hand for exactly this reason; that logic belongs in frob.
3. Decide the ownership rule per verb: which verbs are legitimate inside a worktree (start, evidence, done-report on the ticket being worked), and which should refuse or warn (new/close/drop targeting a ticket the worktree does not own). This overlaps T-1669's ownership model -- fold it in there if that is the cleaner home.

Supersedes the narrow framing of T-1638, which should become a child of this.