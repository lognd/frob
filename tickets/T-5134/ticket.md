---
id: T-5134
title: 'Remove ticket citations (T-####) from all user-facing help and docs: argparse
  help strings, docs/, refusal and remedy text'
state: done
kind: docs
origin: human
created: '2026-09-20'
priority: high
parent: T-2994
tier: story
sprint: null
runs_last: false
milestone: 1.0.0
flavour: user_story
due: null
rank: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5134
branch: t-5134
scope:
- src/frob/_cli_parsers/*.py
- tests/unit/coordinator_suite/test_count_ticket_citations.py
- scripts/count_ticket_citations.py
- scripts/strip_help_citations.py
- docs/commands/ack.md
- docs/commands/clean.md
- docs/commands/doctor.md
- docs/commands/gitlog.md
- docs/commands/graph.md
- docs/commands/map.md
- docs/commands/mutate.md
- docs/commands/perf.md
- docs/commands/release.md
- docs/commands/serve.md
- docs/commands/status.md
- docs/commands/test.md
- docs/commands/vet.md
- docs/design/cwe-1000-registry.md
- docs/guides/command-reference.md
- docs/guides/editors.md
- docs/guides/extending/cve-fingerprints.md
- docs/guides/extending/design-lint-rules.md
- docs/guides/extending/failure-injection-acceptance-criteria.md
- docs/guides/extending/pii-categories.md
- docs/guides/extending/prover-claim-kinds.md
- docs/guides/extending/scenario-kinds.md
- docs/guides/extending/ticket-kinds-states.md
- docs/guides/frob-toml.md
- tests/unit/coordinator_suite/test_strip_help_citations.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: true
scope_breadth_ack_reason: 'owner directive 2026-09-20: a repo-wide text migration;
  each file is a mechanical citation strip'
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/**/*.md
  reason: a repo-wide docs glob leases every docs ticket's files; docs citations are
    added by file once measured
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/modules/gates.md
  reason: ARGHELP001 gate needs a rule-table row and section like every other gate;
    not part of the bulk citation-removal pass
  actor: logan
  at: '2026-09-22'
- op: remove
  glob: docs/modules/gates.md
  reason: gate-framework wiring reverted -- staying within declared scope; enforcement
    lives in scripts/ instead
  actor: logan
  at: '2026-09-22'
- op: add
  glob: tests/unit/coordinator_suite/test_count_ticket_citations.py
  reason: positive-control test for scripts/count_ticket_citations.py, this ticket
    own tool
  actor: logan
  at: '2026-09-22'
- op: add
  glob: scripts/count_ticket_citations.py
  reason: 'new measurement/removal tooling this ticket requires (frob ticket body:
    write a script under scripts/)'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: scripts/strip_help_citations.py
  reason: 'new measurement/removal tooling this ticket requires (frob ticket body:
    write a script under scripts/)'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/ack.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/clean.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/doctor.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/gitlog.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/graph.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/map.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/mutate.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/perf.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/release.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/serve.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/status.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/test.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/vet.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/design/cwe-1000-registry.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/command-reference.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/editors.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/extending/cve-fingerprints.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/extending/design-lint-rules.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/extending/failure-injection-acceptance-criteria.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/extending/pii-categories.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/extending/prover-claim-kinds.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/extending/scenario-kinds.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/extending/ticket-kinds-states.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/frob-toml.md
  reason: docs prose T-#### citation removal, small single-citation files measured
    by scripts/count_ticket_citations.py --scope docs
  actor: logan
  at: '2026-09-22'
- op: add
  glob: tests/unit/coordinator_suite/test_strip_help_citations.py
  reason: positive-control/coverage test for scripts/strip_help_citations.py, the
    other tool T-5134 ships
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: frob:doc anchors required for the 6 new public symbols in scripts/count_ticket_citations.py
    and scripts/strip_help_citations.py
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindHelpCitations::test_positive_control_plants_a_citation_the_detector_must_report
- tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations::test_prose_citation_is_reported
- tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations::test_directive_grammar_example_is_exempt
designated_repro_test: null
acceptance:
- text: given the full CLI, when every 'frob ... --help' output is captured, then
    no output contains a T-#### token
  evidence:
  - tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindHelpCitations::test_positive_control_plants_a_citation_the_detector_must_report
  - tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations::test_prose_citation_is_reported
- text: given docs/ excluding docs/audits and the tickets tree, when scanned, then
    no prose line contains a T-#### token
  evidence:
  - tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations::test_prose_citation_is_reported
  - tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations::test_directive_grammar_example_is_exempt
- text: given a new help= string containing T-1234, when frob check runs, then the
    DOC lint fires with the file and line
  evidence:
  - tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindHelpCitations::test_positive_control_plants_a_citation_the_detector_must_report
  - tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations::test_prose_citation_is_reported
threat: null
component: cli
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: ticket prose (T-#### citations) is removed in its entirety from frob documentation and help. Measured: 462 T-#### mentions across src/frob/_cli_parsers/*.py alone (visible in every --help output, e.g. 'free-form sprint commitment label (e.g. 2026-W30, sprint-14, T-0715)'), plus the docs/ prose T-4422 (DOC012) already covers. Scope of THIS story: (1) argparse help/description/epilog strings in src/frob/_cli_parsers and any runner-side help text: strip the citation, keep the sentence, move any WHY worth keeping into the ticket ledger or a docs/design page; (2) refusal and remedy messages the user reads at the terminal (the 'T-2006 dropped N stale...' log lines are fine as INFO logs, but ERROR text and remedies must not cite tickets); (3) docs/ prose beyond T-4422's DOC012 scope: tables, headings, code-fence captions; (4) a lint so it cannot recur: extend DOC012 (or add DOC013) to fire on a T-#### token inside an argparse help= / description= string literal and inside docs/ prose outside the tickets ledger and docs/audits history; the ledger, done-reports, frob:ticket directive comments, commit messages and CHANGELOG remain the only homes for ticket ids. Coordinate with T-4422 (docs prose) and T-4691 (source comment narrative) so the three stories do not collide on the same files: this story owns _cli_parsers and user-facing message strings; T-4422 owns docs/ prose; T-4691 owns source comments.