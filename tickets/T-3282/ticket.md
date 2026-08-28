---
id: T-3282
title: frob ticket migrate --to v2 silently no-ops on a zero-ticket v1 ledger, leaving
  LEDGERV1001 unresolvable via its own documented remedy
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store_migrate.py
- src/frob/app/ticket_runner/_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: record confirmed repro and root cause from T-3272 investigation
  actor: logan
  at: '2026-08-28'
  old_length: 0
  new_length: 3171
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CONFIRMED by direct repro (T-3272's investigation, coordinator-flagged as a
second bug hiding behind FROBLEMS F-006):

    mkdir repro && cd repro && git init -q
    cat > tickets.md <<'INNER'
    # Tickets

    Central ledger managed by `frob ticket` -- one section per ticket.
    Run `frob ticket new` to add one, `frob ticket doable` to see what is
    ready.
    INNER
    frob ticket migrate --to v2
    # -> "tickets: already v2-mode (or nothing to migrate)"
    # tickets/ is NEVER created; tickets.md is untouched.

`_store_mode` correctly reports this repo as "single" (v1) -- `ledger_path`
exists, no `tickets/T-*/ticket.md` tree does. LEDGERV1001 correctly fires,
naming `frob ticket migrate --to v2` as the remedy. But `migrate_v1_to_v2`
parses zero tickets out of the (structurally valid, contentwise empty)
monofile, so it writes zero v2 ticket files and returns `Ok(0)` -- the exact
same return value `_migrate`'s CLI wrapper (`src/frob/app/ticket_runner/
_query.py::_migrate`) uses to mean "already v2, nothing to do". The log
message is ambiguous between the two very different states ("this repo was
already fine" vs "this repo is v1 and my documented remedy just silently
declined to fix it"), and more importantly: the repo is left in EXACTLY the
same v1 state it started in. Re-running the command changes nothing.
LEDGERV1001 keeps firing forever on a repo that has done everything the
gate told it to do.

ROOT CAUSE: `migrate_v1_to_v2` never actually flips `_store_mode` for a
zero-ticket ledger, because v2-mode is detected purely structurally
(`_v2_glob`: does `tickets/T-*/ticket.md` exist) and there is nothing to
write when there are zero source tickets. The monofile itself is also never
deleted by this migrator (by design -- it is meant to be reversible), so
"v1 with a lingering empty ledger" and "v2 already" are indistinguishable
from the return value alone.

SUGGESTED FIX (for whoever picks this up, not decided here): either (a)
`migrate_v1_to_v2` deletes/renames the empty monofile once it has confirmed
zero tickets are in it (nothing left to lose by deleting an empty ledger),
so `_store_mode` flips to "v2" on the very next call and LEDGERV1001 clears;
or (b) the CLI distinguishes "was already v2" from "v1, migrated 0 because
there were 0 tickets to migrate" and prints an actionable message in the
second case (e.g. "no tickets to migrate; delete tickets.md yourself or run
frob ticket migrate --to v2 --force-empty" or similar) instead of the
current ambiguous "already v2-mode (or nothing to migrate)".

NOT blocking T-3272: T-3272's fix (stop writing tickets.md at scaffold
time) means brand-new repos never enter this state at all -- they start
with no ledger content of any shape, which `_store_mode` already treats as
v2 (T-1553). This ticket covers EXISTING v1 repos with an empty/near-empty
ledger, which are unaffected by the scaffold-side fix.

ACCEPTANCE
- `frob ticket migrate --to v2` on a zero-ticket v1 ledger either clears
  LEDGERV1001 on the next `frob check`, or the CLI's message makes clear
  that manual deletion of tickets.md is required and why.
- A regression test reproducing the exact repro above.
