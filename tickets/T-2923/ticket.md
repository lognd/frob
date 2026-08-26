---
id: T-2923
title: 'frob sys shrink: tighten unobserved may= capabilities, never widen'
state: in-progress
kind: feature
origin: human
created: '2026-08-25'
priority: high
parent: T-2920
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_shrink.py
- src/frob/strata/__init__.py
- tests/unit/strata/test_shrink.py
- src/frob/app/sys_runner.py
- src/frob/_cli_parsers/_misc.py
- docs/commands/sys.md
- design/frob.strata
- src/frob/app/_config_external.py
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: narrow to the new shrink module + its __init__ export + its own test file;
    CLI wiring already covered by the ticket's implicit_scope grant
  actor: logan
  at: '2026-08-25'
- op: remove
  glob: design/**
  reason: narrow to the new shrink module + its __init__ export + its own test file;
    CLI wiring already covered by the ticket's implicit_scope grant
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/strata/_shrink.py
  reason: narrow to the new shrink module + its __init__ export + its own test file;
    CLI wiring already covered by the ticket's implicit_scope grant
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/strata/__init__.py
  reason: narrow to the new shrink module + its __init__ export + its own test file;
    CLI wiring already covered by the ticket's implicit_scope grant
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/strata/test_shrink.py
  reason: narrow to the new shrink module + its __init__ export + its own test file;
    CLI wiring already covered by the ticket's implicit_scope grant
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: CLI wiring for the new frob sys shrink verb lives in these two files, alongside
    the implicit __main__.py/config.py/ticket_runner grant
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: CLI wiring for the new frob sys shrink verb lives in these two files, alongside
    the implicit __main__.py/config.py/ticket_runner grant
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/commands/sys.md
  reason: documenting the new frob sys shrink verb
  actor: logan
  at: '2026-08-25'
- op: add
  glob: design/frob.strata
  reason: declaring fs.read/fs.write may grants for the new _shrink.py module -- SYS100
    fired on my own diff since the new module performs real fs.read/fs.write; declared
    by hand, never auto-widened
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/_config_external.py
  reason: CLI dest sys_shrink_check needs wiring into the forwarding-layer field-copy
    tuple (WIRE001/FLAGCOV001)
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 ratchet ceiling raise for the fs.read/fs.write/net via-lists this
    ticket's new files genuinely grew
  actor: logan
  at: '2026-08-25'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2920
  reason: child implementation ticket of the T-2920 shrink-only ratchet epic
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

Child of epic T-2920 (see that ticket's full design). SYS101 (a capability
DECLARED in a node's `may` atoms with zero observed sites) is currently a
standing warning nobody acts on: the loose direction never actually
shrinks the interface. Need a `frob sys shrink` command that
auto-TIGHTENS only:

- drop a declared capability from a node's `may` list when the scanner
  observes zero sites for it anywhere in that node's `code=`-bound files
  (SYS101's own condition, reversed into a fix instead of a standing warn)
- narrow an over-broad `code=` glob to the files that actually exist /
  are actually bound

This ticket does NOT touch the SYS100 widening direction (capability
escalation) at all -- that stays an error, unconditionally, with no
auto-fix of any kind reachable through this new command or any flag on
it. `_sync_may.py`'s existing WIDENING functions
(sync_may_report/apply_sync_may/sync_may_extended_report/
apply_sync_may_extended) are OUT OF SCOPE for this ticket: T-2922 (blocks
the parent epic) owns unwiring their caller in gates/_fix_engine_sync.py.
Leave them physically in place, untouched, uncalled by anything this
ticket adds.

SYS103 (a capability-bearing file no node's `code=` binds) also stays an
untouched error: `frob sys shrink` must never auto-bind an unbound file.

## Acceptance

- `frob sys shrink [--check] [--path DIR]`: for a node whose `may=`
  declares a capability the scanner never observes, tightens (removes)
  it; diff is reviewable (writes `.strata` text, same posture as the
  existing `_sync_may.py` writer). `--check` reports without writing.
- Given a node's code performs a capability its `may=` does not grant
  (SYS100), `frob sys shrink` makes NO change and refuses with a message
  saying so explicitly if asked to touch that node's escalation --
  shrink only ever narrows the SYS101 direction, never touches SYS100.
- Given a capability-bearing file no node's `code=` binds (SYS103),
  `frob sys shrink` does not bind it, and the finding stays an error.
- Must-fire fixtures (new, isolated design/.strata fixtures under this
  ticket's own test tree, not frob's own design/):
  - a node acquiring `net` it never declared (SYS100) -- must remain an
    ERROR after `frob sys shrink` runs; `may=` is byte-for-byte
    unchanged.
  - a capability-bearing unbound file (SYS103) -- must remain an ERROR;
    no node's `code=` gains the file after shrink runs.
- Must-still-pass control: frob's OWN repo (design/frob.strata) keeps 0
  SYS errors, and its SYS200-205 finding count is IDENTICAL before and
  after this ticket's change (measure both, report both numbers).
- Scoped proof (NOT epic-wide -- the epic-wide "no widening path exists
  anywhere" claim stays open pending T-2922): a test asserting the shrink
  code path this ticket adds has no widening branch, and that no flag/
  env var/config key on `frob sys shrink` reaches a widening operation.
  This does not, and must not claim to, prove `_sync_may.py`'s existing
  functions are unreachable -- that is T-2922's closing step.
