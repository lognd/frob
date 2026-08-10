---
id: T-1697
title: 'frob verify: surface the unverified window -- depth, age, quarantine, attribution'
state: done
kind: ux
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1687
parent: T-1686
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- docs/modules/tickets.md
- src/frob/app/config.py
- src/frob/app/app.py
- src/frob/__main__.py
- src/frob/verify/_quarantine.py
- tests/unit/verify/test_quarantine.py
- tests/unit/verify/test_verify_runner.py
- tests/unit/test_verify_cli_parser.py
- src/frob/app/_config_external.py
- src/frob/_cli_parsers/__init__.py
- docs/modules/app.md
- tickets/T-1847/ticket.md
- README.md
- docs/modules/cli.md
- docs/design/cli-regrouping.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: new CLI verb needs Subcommand enum, runner dict, and __main__ wiring beyond
    the two named new files; dispose path needs quarantine.py edits + its own tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/app.py
  reason: new CLI verb needs Subcommand enum, runner dict, and __main__ wiring beyond
    the two named new files; dispose path needs quarantine.py edits + its own tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/__main__.py
  reason: new CLI verb needs Subcommand enum, runner dict, and __main__ wiring beyond
    the two named new files; dispose path needs quarantine.py edits + its own tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: new CLI verb needs Subcommand enum, runner dict, and __main__ wiring beyond
    the two named new files; dispose path needs quarantine.py edits + its own tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: new CLI verb needs Subcommand enum, runner dict, and __main__ wiring beyond
    the two named new files; dispose path needs quarantine.py edits + its own tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: new CLI verb needs Subcommand enum, runner dict, and __main__ wiring beyond
    the two named new files; dispose path needs quarantine.py edits + its own tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_verify_cli_parser.py
  reason: new CLI verb needs Subcommand enum, runner dict, and __main__ wiring beyond
    the two named new files; dispose path needs quarantine.py edits + its own tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: argparse Namespace -> AppConfig copy loop lives here; verify_* fields must
    be registered in its field tuples or the CLI parses but never reaches the runner
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: the parser-builder re-export module must register _add_verify_parser alongside
    every sibling builder
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: docs/modules/app.md gained an AFFECT001-required note; README.md/cli.md
    need the new frob verify command table row; the draft ticket file is my own filed
    follow-up
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1847/ticket.md
  reason: docs/modules/app.md gained an AFFECT001-required note; README.md/cli.md
    need the new frob verify command table row; the draft ticket file is my own filed
    follow-up
  actor: logan
  at: '2026-08-08'
- op: add
  glob: README.md
  reason: docs/modules/app.md gained an AFFECT001-required note; README.md/cli.md
    need the new frob verify command table row; the draft ticket file is my own filed
    follow-up
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: docs/modules/app.md gained an AFFECT001-required note; README.md/cli.md
    need the new frob verify command table row; the draft ticket file is my own filed
    follow-up
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: AFFECT001 required touching the _GroupedHelpFormatter affects-closure doc
    after the __main__.py help-string edit
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_reports_depth_age_and_quarantine
- tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_clean_when_nothing_queued_and_no_quarantine
- tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_watermark_reported_when_present
- tests/unit/verify/test_verify_runner.py::TestDispose::test_dismiss_disposes_the_live_unattributed_finding
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
An unverified window nobody can see is a liability pretending to be a
feature. This is the leaf that makes the whole epic auditable, and it is
high priority despite being "just CLI": every other leaf's failure mode
is discovered through this surface.

`frob verify status`: the watermark commit and its age, unverified depth,
the oldest unverified entry, quarantine state with the batch and findings
that raised it, and the last batch's outcome including anything
UNATTRIBUTED. Human-readable by default, `--json` for agents.

`frob verify now`: drain and verify synchronously, for a human who wants
the window closed before walking away.

`frob verify explain <finding>`: print the attribution path -- the
reachability chain that assigned this finding to this commit -- so an
attribution can be audited rather than trusted.

Porcelain rule: exit non-zero when quarantine is raised, so a shell or CI
step can gate on "is this repo's verification healthy" without parsing
prose.

Acceptance: `status` reports depth/age/quarantine accurately against a
seeded queue; `--json` round-trips through a pydantic model; a raised
quarantine exits non-zero; `explain` prints a reachability path for an
attributed finding.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.