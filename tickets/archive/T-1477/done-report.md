## Done report

Drained NEGEXIST001, DOC004/DOC006, and part of COV006/COV007 (WAIVE004
could not be measured -- see below). WAIVE004's own gate design only
computes on a genuinely unscoped `frob check` (no --only/--ticket at
all, `full_unscoped_run=not cfg.gates and cfg.ticket is None`), which
this repo's own agent playbook section 3b/3c reserves for the
coordinator (a bare check exceeds the foreground timeout and, under
FROB_AGENT, is refused outright). No --only chunking substitutes for
it -- every --only invocation sets cfg.gates, which forces
full_unscoped_run=False. This is a real, disclosed gap in the brief's
own premise, not a corner I cut: WAIVE004 needs a coordinator-run
unscoped `frob check` to measure honestly at all.

Per-class before/after (measured via `frob check --only docblocks
--only coverage`, unscoped, from this worktree):

- NEGEXIST001: 39 -> 3. The 3 remaining are absence-claims I bound via
  `frob:until` to newly-filed draft tickets (T-1480 sys
  phase-5 verbs, T-1483 refactor CLI wiring,
  T-1479 daemon-proxy wiring) -- the directive regex
  (`T-\d+`) cannot match a `T-draft-<hex>` id, so these read UNBOUND
  until `frob ticket land` renumbers the drafts to real numeric ids
  (T-1125 rewrites prose citations at land; whether it also rewrites
  frob:until directives specifically was not verified in this session).
  Everything else genuinely resolved: reworded 30 historical/
  descriptive claims (audits, design corpora, timeless mechanics) to
  drop the trigger phrasing without changing meaning, and bound 3
  more genuinely-open gaps to newly-filed tickets (T-1482
  policy refinement-monotonicity, T-1478 T-1440 argument-
  scope follow-up, T-1481 --fix CLI wiring).
  ONE exception disclosed: CHANGELOG.md:607's claim could not be fixed
  in-worktree -- CHANGELOG.md is land-owned (T-0731's pre-commit guard
  refuses any worktree commit touching it). Reworded then reverted;
  still live as 1 of the "3 remaining" is NOT this one (that one isn't
  in the NEGEXIST001 output at all currently -- it may only surface on
  a fuller unscoped run than --only docblocks exercises, or needs land
  itself to fix). Flagging so it isn't silently dropped.

- DOC004: 1 -> 0. DOC006: 25 -> 0. All resolved: fixed stale
  file/symbol pointers to their real post-split locations
  (_capability_core.py, _threat_catalog_cwe.py, _threat_discharge.py,
  _cli_parsers/_ticket/**, app/ticket_runner/**), fixed two broken
  heading-anchor slugs (recomputed via the real slugify() rules) and
  one placeholder anchor, and added targeted frob:waive DOC004/DOC006
  (inline, immediately before the flagged pointer -- matching this
  repo's own established convention, see docs/design/ledger-v2.md) for
  genuinely illustrative examples and disclosed-not-done/proposed-
  future prose in tickets.md.

- COV006/COV007: 41 -> 28 unwaived (13 resolved). Fixed: moved 10
  private-symbol frob:doc anchors in src/frob/gates/__init__.py,
  _sys.py, _sys_selfaudit.py onto their real public gate entrypoints
  (scope_gate, release_gate, run_gates, sys_gate) instead of leaving
  them on internal helpers with no single public caller; same pattern
  in src/frob/strata/_compliance.py (check_cmpl_registry) and
  _mutation_audit.py (run_may_mutation_audit). NOT completed: the
  remaining ~9 COV007 (strata/_effects.py, _selfconform.py x3,
  tickets/_land.py, _land_squash.py x3, release/__init__.py,
  app/_daemon_proxy.py, app/ticket_runner/_land_cmd.py x5,
  strata/_compliance.py's _CMPL_UNIT_TRIAGE_TICKET) and all 12 COV006
  (frob:tests edges needing rebinding to a symbol the test actually
  calls, which requires reading each test body) remain open --
  disclosed, not silently dropped. Left the ticket in-progress rather
  than closing it dishonestly against an incomplete acceptance.

One in-flight self-regression caught and fixed: rewording
FlakeError.TicketUnresolvable's string value (to drop a NEGEXIST001-
triggering doc-embedded code excerpt) tripped COV002 (changed public
symbol, no frob:ticket edge) -- bound via frob:ticket T-1477
on the class.

Filed tickets (drafts, renumber at land):
- T-1483: wire frob refactor into main CLI dispatch
- T-1480: build frob sys check/trace/capacity/threats verbs
- T-1481: wire frob check --fix CLI flag to the tiered fix engine
- T-1479: wire remaining daemon-proxy subcommands named by T-0321's integration map
- T-1482: build policy refinement-monotonicity diff pass (INV-030)
- T-1478: argument-level may scoping (T-1440 follow-up)

Evidence: docs-only class of change plus a handful of gates/**
frob:doc-anchor moves with no new runtime behavior; no new pytest
surface of its own. Per playbook section 5, recording the existing
CLI-dispatch integration test:
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

### Changed
```
 docs/audits/docs-staleness-2026-07-29.md         |  27 +--
 docs/audits/frob-blindspots-2026-07-23.md        |   2 +-
 docs/audits/test005-zero-classification-t1418.md |   3 +-
 docs/commands/refactor.md                        |   2 +
 docs/commands/sys.md                             |   2 +
 docs/design/check-fix-engine.md                  |   8 +-
 docs/design/coding-performance-corpus.md         |   2 +-
 docs/design/design-pattern-traps-corpus.md       |   7 +-
 docs/design/registry/README.md                   |   4 +-
 docs/design/registry/RECONCILIATION.md           |   4 +-
 docs/design/secrets-pii-corpus.md                |   2 +-
 docs/design/security-corpus.md                   |   5 +-
 docs/design/supply-chain-corpus.md               |   2 +-
 docs/guides/agent-playbook.md                    |   2 +-
 docs/guides/agentic-time-profiling.md            |   3 +-
 docs/guides/editors.md                           |   2 +-
 docs/guides/extending/capability-registry.md     |   2 +-
 docs/guides/extending/design-lint-rules.md       |   2 +-
 docs/guides/extending/prover-claim-kinds.md      |   4 +-
 docs/guides/extending/sys-export-formats.md      |   2 +-
 docs/modules/app.md                              |   2 +-
 docs/modules/decisions.md                        |   2 +-
 docs/modules/fleet.md                            |   4 +-
 docs/modules/serve.md                            |   2 +
 docs/modules/testing.md                          |   6 +-
 docs/modules/tickets.md                          |  11 +-
 docs/modules/vet.md                              |  10 +-
 docs/strata/krb.md                               |   2 +-
 docs/strata/policy.md                            |  11 +-
 docs/strata/surface.md                           |  13 +-
 docs/strata/threat.md                            |   4 +-
 src/frob/gates/__init__.py                       |  11 +-
 src/frob/gates/_sys.py                           |   1 +
 src/frob/gates/_sys_selfaudit.py                 |   2 -
 src/frob/strata/_compliance.py                   |   2 +-
 src/frob/strata/_mutation_audit.py               |   5 +-
 src/frob/testing/_stability.py                   |   3 +-
 tickets.md                                       | 261 +++++++++++++++++++++--
 38 files changed, 339 insertions(+), 100 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 5330 warning(s), 740 waived
- error-findings: none (measured, zero errors)
