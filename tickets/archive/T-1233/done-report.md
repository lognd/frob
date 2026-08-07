## Done report

Fixed every confirmed class-A and class-B finding in
docs/audits/docs-staleness-2026-07-29.md across five per-directory
batches (commands/, guides/, modules/+design/, strata/, top-level+audits).
Class-A DOC006/DOC004 warnings for arch.md:1825, testing.md:526, and
install.md:494/525/564 confirmed cleared via `frob check --only docanchor
--only docblocks` (0 errors both before and after; the 33 pre-existing
warnings are all outside this ticket's scope -- design/refactor-verb.md,
design/check-fix-engine.md, design/ledger-v2.md, gates.md, tickets.md,
invariants/INV-041.md -- unchanged by this ticket's edits).

### Changed
```
 FROBLEMS.md                                        |  5 +-
 docs/audits/README.md                              | 11 ++--
 docs/audits/tickets-testing.md                     |  6 ++
 docs/commands/check.md                             | 10 +--
 docs/commands/cycle.md                             |  2 +-
 docs/commands/deploy.md                            |  4 +-
 docs/commands/gitlog.md                            |  2 +-
 docs/commands/map.md                               |  5 +-
 docs/commands/outline.md                           |  3 +-
 docs/commands/parse.md                             |  2 +
 docs/commands/scaffold.md                          | 20 +++---
 docs/commands/sys.md                               |  3 +-
 docs/commands/xref.md                              |  2 +-
 docs/design/coding-performance-corpus.md           | 12 +++-
 docs/design/design-pattern-traps-corpus.md         | 11 ++--
 docs/design/language-adapter-tier-decision.md      | 11 ++--
 docs/design/system-performance-corpus.md           | 14 ++--
 docs/guides/agent-playbook.md                      | 14 ++--
 docs/guides/editors.md                             |  7 +-
 docs/guides/exhaustive-research.md                 |  2 +-
 docs/guides/extending/README.md                    |  6 +-
 docs/guides/extending/benign-capabilities.md       |  4 +-
 docs/guides/extending/capability-registry.md       | 34 +++++-----
 docs/guides/extending/comment-dsl-directives.md    | 17 +++--
 docs/guides/extending/dup-detector-registry.md     | 18 +++---
 docs/guides/extending/gate-rule-families.md        | 10 ++-
 docs/guides/extending/language-grammar-handlers.md | 20 +++---
 docs/guides/extending/pii-categories.md            |  4 +-
 docs/guides/extending/prover-claim-kinds.md        | 13 ++--
 docs/guides/extending/scenario-kinds.md            |  7 +-
 docs/guides/extending/secrets-scan-providers.md    |  2 +-
 docs/guides/extending/strata-surface-grammar.md    | 23 ++++---
 docs/guides/extending/ticket-kinds-states.md       | 18 ++++--
 docs/guides/install.md                             |  3 +
 docs/index.md                                      | 18 +++---
 docs/modules/app.md                                | 41 ++++++++++++
 docs/modules/arch.md                               | 41 ++++++++++--
 docs/modules/bind.md                               |  2 +-
 docs/modules/clean.md                              |  7 +-
 docs/modules/cli.md                                | 18 ++++--
 docs/modules/dup.md                                |  7 +-
 docs/modules/graph.md                              | 32 ++++++---
 docs/modules/lang.md                               | 33 ++++++----
 docs/modules/mutate.md                             |  2 +-
 docs/modules/perf.md                               |  9 +--
 docs/modules/serve.md                              | 16 +++--
 docs/modules/strata.md                             | 17 ++---
 docs/modules/testing.md                            |  7 +-
 docs/modules/vet.md                                | 40 +++++++-----
 docs/rework.md                                     |  4 +-
 docs/strata/evidence.md                            | 12 ++--
 docs/strata/host.md                                | 16 +++--
 docs/strata/kernel.md                              |  2 +-
 docs/strata/krb.md                                 |  4 +-
 docs/strata/reliability.md                         |  6 +-
 docs/strata/roadmap.md                             | 53 +++++++++------
 docs/strata/selfconform.md                         | 75 ++++++++++++----------
 docs/strata/surface.md                             | 53 ++++++++-------
 docs/strata/threat.md                              | 10 +--
 docs/strata/waive.md                               | 28 ++++----
 tickets.md                                         |  2 +-
 61 files changed, 540 insertions(+), 340 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 2707 warning(s), 676 waived
- error-findings: PRE001@tickets/T-1233
