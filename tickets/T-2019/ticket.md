---
id: T-2019
title: Re-verify 10 already-landed BUG002 repro designations against T-2005's PYTHONPATH
  fix
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets/T-1546/ticket.md
- tickets/T-1670/ticket.md
- tickets/T-1749/ticket.md
- tickets/T-1838/ticket.md
- tickets/T-1841/ticket.md
- tickets/T-1848/ticket.md
- tickets/T-1853/ticket.md
- tickets/T-1861/ticket.md
- tickets/T-1882/ticket.md
- tickets/T-1907/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2005 fixed a bug where `_run_designated_test`'s PYTHONPATH override was
silently dropped (`run_argv` had no `env` parameter), so a bug/security
ticket's BUG002 repro verdict could read PASSED_AT_PARENT against the
CURRENT (already-fixed) source instead of the actual parent commit's
source, for any pure-Python-only fix.

10 already-landed tickets carry a non-null `designated_repro_test` and
are therefore suspect: T-1546, T-1670, T-1749, T-1838, T-1841, T-1848,
T-1853, T-1861, T-1882, T-1907 (denominator: `git grep -l
"designated_repro_test:" tickets/archive` filtered to non-null).

Re-verify each: `frob ticket evidence <id> --check-repro <designated
node-id> --base-ref <the ticket's own recorded parent commit>` under the
now-fixed `run_argv`, and confirm the verdict is unchanged
(FAILED_AT_PARENT, not a newly-discovered PASSED_AT_PARENT). Any ticket
whose verdict FLIPS to PASSED_AT_PARENT under the fix had confirmatory-
only evidence all along and needs its own follow-up (stronger evidence,
or an honest disclosure that the fix cannot currently be proven).
