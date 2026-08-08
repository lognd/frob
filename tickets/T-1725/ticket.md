---
id: T-1725
title: Hooks and docs reference frob verbs by name with nothing checking they resolve;
  gate it before the CLI regrouping renames them
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/frob-timeout-guard.py
- .claude/hooks/frob-suggest.py
- src/frob/gates/_wire.py
- docs/modules/gates.md
- src/frob/gates/_waive.py
- tests/test_gates.py
- src/frob/gates/_pii_structural/_keywords.py
- tickets/T-1725/ticket.md
- tickets/T-1725/done-report.md
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: WIRE003 registration in _KNOWN_GATE_RULES; the new gate's own regression
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates.py
  reason: WIRE003 registration in _KNOWN_GATE_RULES; the new gate's own regression
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_pii_structural/_keywords.py
  reason: PII012 'token' homonym allowlist entries for the new WIRE003 identifiers;
    v2 ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1725/ticket.md
  reason: PII012 'token' homonym allowlist entries for the new WIRE003 identifiers;
    v2 ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1725/done-report.md
  reason: PII012 'token' homonym allowlist entries for the new WIRE003 identifiers;
    v2 ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: REG010 registry sync entry for the new CHK-GATE-WIRE003 self-audit id
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates.py::TestWireGate::test_wire003_matcher_pattern_stale_verb_is_flagged
- tests/test_gates.py::TestWireGate::test_wire003_suggestion_string_stale_verb_is_flagged
- tests/test_gates.py::TestWireGate::test_wire003_real_verbs_are_not_flagged
- tests/test_gates.py::TestWireGate::test_wire003_dotted_module_path_is_not_flagged
designated_repro_test: null
threat: null
component: null
---
The PreToolUse hooks in `.claude/hooks/` reference frob verbs BY NAME, as
plain strings, and nothing checks that those names resolve. The CLI
regrouping work (T-1567..T-1571) renames and regroups verbs. A rename will
silently break every reference, and the failure mode is the worst kind:
the hook keeps running and keeps passing.

Concrete references today:

- `frob-timeout-guard.py` matches `frob +(ticket +(land|done-report)|check|
  test)` to decide whether a command needs a large tool timeout. Rename or
  regroup any of those four and the guard stops firing -- silently. The
  stall pattern it exists to prevent comes straight back, and nothing says
  the guard went blind.
- `frob-suggest.py` SUGGESTS `uv run frob test`, `frob check`, `frob ticket
  ...`, `frob coverage`, `frob worktree` in its refusal text. After a
  rename these become instructions to run a command that no longer exists
  -- a hook that blocks a caller and then tells it to do something
  impossible, which is the T-1705 failure exactly.

Both are now git-tracked (`.claude/hooks/**`), so a gate can see them.

Two pieces of work:

1. A DETECTOR. A rule (register a real id in the catalog; do not invent an
   unregistered one) that extracts frob verb references from tracked hook
   sources and fails when one does not resolve against the live CLI
   dispatch table. Resolve against the DISPATCH TABLE, not a hand-written
   list of verb names -- a hand-written list is the same defect class as
   the bug, and it will drift the first time someone adds a verb.

   Both reference SHAPES must be covered: the regex/matcher form
   (`frob-timeout-guard`'s PATTERN) and the prose form inside suggestion
   strings. The second is easy to forget because it is "just a message",
   and it is precisely the half that misleads a human.

2. SEQUENCING. T-1567..T-1571 are blocked on this, deliberately. The
   detector has to exist BEFORE the renames, or the renames are exactly
   the event it cannot warn about. Landing it afterwards means hand-auditing
   the hooks and hoping.

Note for whoever does the regrouping afterwards: keeping the old verb as a
deprecated alias does NOT make this unnecessary. The hooks would keep
working while every suggestion string tells callers to use a verb the help
output no longer documents, which is drift with a longer fuse.

Wider scope, worth checking while here rather than filing again: the same
by-name coupling exists anywhere outside `src/` that names a frob verb --
`docs/guides/agent-playbook.md`, `docs/modules/cli.md`, the scaffold
templates, and any CI recipe. The detector should cover tracked
non-source references generally, not hooks specifically. Report what it
finds; the count is itself the argument for how bad the coupling is.