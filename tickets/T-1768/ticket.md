---
id: T-1768
title: frob release stamp --allow-unbumped silently rebaselines the REL001 manifest
  with no reason and no audit record
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/release/__init__.py
- tests/test_release.py
- docs/modules/gates.md
- src/frob/app/release_runner.py
- src/frob/_cli_parsers/_misc.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/tickets/_force_override.py
- docs/modules/release.md
- tests/unit/test_release_stamp_guard.py
- tickets/T-1768/ticket.md
- tickets/T-1768/done-report.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_reporting.py
  reason: flag actually lives in _cli_parsers/_misc.py, not _reporting.py -- narrowing
    to real files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/release_runner.py
  reason: the --allow-unbumped flag and its CLI wiring live in app/release_runner.py
    + _cli_parsers/_misc.py + config, not _reporting.py; reusing the T-1762 record_force_override
    primitive needs _force_override.py in scope; docs/release.md and the existing
    stamp-guard test file are the real doc/test homes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: the --allow-unbumped flag and its CLI wiring live in app/release_runner.py
    + _cli_parsers/_misc.py + config, not _reporting.py; reusing the T-1762 record_force_override
    primitive needs _force_override.py in scope; docs/release.md and the existing
    stamp-guard test file are the real doc/test homes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/config.py
  reason: the --allow-unbumped flag and its CLI wiring live in app/release_runner.py
    + _cli_parsers/_misc.py + config, not _reporting.py; reusing the T-1762 record_force_override
    primitive needs _force_override.py in scope; docs/release.md and the existing
    stamp-guard test file are the real doc/test homes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/_config_external.py
  reason: the --allow-unbumped flag and its CLI wiring live in app/release_runner.py
    + _cli_parsers/_misc.py + config, not _reporting.py; reusing the T-1762 record_force_override
    primitive needs _force_override.py in scope; docs/release.md and the existing
    stamp-guard test file are the real doc/test homes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_force_override.py
  reason: the --allow-unbumped flag and its CLI wiring live in app/release_runner.py
    + _cli_parsers/_misc.py + config, not _reporting.py; reusing the T-1762 record_force_override
    primitive needs _force_override.py in scope; docs/release.md and the existing
    stamp-guard test file are the real doc/test homes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/release.md
  reason: the --allow-unbumped flag and its CLI wiring live in app/release_runner.py
    + _cli_parsers/_misc.py + config, not _reporting.py; reusing the T-1762 record_force_override
    primitive needs _force_override.py in scope; docs/release.md and the existing
    stamp-guard test file are the real doc/test homes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_release_stamp_guard.py
  reason: the --allow-unbumped flag and its CLI wiring live in app/release_runner.py
    + _cli_parsers/_misc.py + config, not _reporting.py; reusing the T-1762 record_force_override
    primitive needs _force_override.py in scope; docs/release.md and the existing
    stamp-guard test file are the real doc/test homes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1768/ticket.md
  reason: 'v2 ledger layout: the ticket''s own per-ticket files are implicitly in
    scope, same as tickets.md was under v1 (T-1678 precedent)'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1768/done-report.md
  reason: 'v2 ledger layout: the ticket''s own per-ticket files are implicitly in
    scope, same as tickets.md was under v1 (T-1678 precedent)'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason::test_refuses_with_no_reason_when_shortfall_is_real
- tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason::test_succeeds_with_reason_and_writes_audit_record
- tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason::test_no_reason_required_when_no_real_shortfall
designated_repro_test: null
threat: null
component: null
runs_last: false
---
`frob release stamp --allow-unbumped` is the third instance of the
silent-override family T-1762 fixed, and arguably the worst of the three.

It permanently rebaselines `.frob-release.json`. No `--reason` flag
exists at all -- not optional-and-unused, absent. Nothing is logged
beyond the flag's own docstring warning, and nothing is recorded.

WHY IT IS WORSE THAN THE TWO ALREADY FIXED. `.frob-release.json` is the
baseline every future REL001 comparison measures against. Rebaselining
it does not merely skip one check -- it silently redefines what counts
as an API change from that moment forward. `archive --force` and
`land --finish --force` bypass a guard for one invocation; this one
alters the standard permanently, and the alteration is invisible in the
ledger, in the logs, and in the diff (a manifest rewrite looks like any
other manifest rewrite).

The flag's own docstring already understands the danger -- "stamping now
would rebaseline the API at the OLD version and silence REL001 without
the release ever happening ... use only with a reason" -- and then does
not require the reason it asks for. That gap between what the help text
demands and what the code enforces is the defect in one line.

This is not hypothetical for this repo. Today four consecutive lands
oscillated the declared version 0.366.0 -> 0.365.0 -> 0.366.0 ->
0.365.0, and the manifest regressed with it; T-1760 fixed the carrying
mechanism. A silent `--allow-unbumped` is the manual equivalent of that
same regression, with a person's intent behind it and no record of what
that intent was.

REQUIRED, mirroring T-1762's landed remedy exactly rather than inventing
a second shape:

1. `--allow-unbumped` requires `--reason`/`--reason-file`, refusing
   without one, as `scope`, `evidence --replace`, `ack`, `archive
   --force` and `land --finish --force` now all do.
2. The bypass appends an append-only audit record naming what was
   rebaselined (the old and new manifest version, and the count of
   symbols whose digests changed), the reason, and the actor -- reusing
   the established `ScopeChangeEntry`/`AckAuditEntry`/
   `EvidenceChangeEntry` shape, not a fifth one.
3. It logs at WARNING naming the baseline it moved and by how much. A
   bypass nobody can see is indistinguishable from the guard not
   existing.

Deliberately NOT in scope: a name-pattern gate for override-shaped flags.
T-1762 examined that and rejected it with reasoning worth preserving --
`--skip-gates` appears in both the needs-a-reason and correctly-free
camps, so the distinction is semantic rather than lexical, and a
name-based rule would false-positive on all 18 `frob check --skip-*`
flags while still requiring a human to read each new flag. Training
reflexive waiving on false positives is the loop that produced 997
waivers in the first place.

Found by the T-1762 agent during its parser-wide audit; filed rather than
absorbed because it lives in `src/frob/release/` -- an entirely different
subsystem from that ticket's `tickets`/`app` scope, and taking on a third
subsystem's scope-closure tax mid-ticket was correctly judged a bad
trade.