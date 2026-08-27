---
id: T-3125
title: frob --help does not list refactor/narrative subcommands
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
- tests/unit/test_main_entry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_main_entry.py
  reason: 'T-3125: help-listing regression test lives here'
  actor: logan
  at: '2026-08-27'
evidence:
- tests/unit/test_main_entry.py::TestHelpListsDirectDispatchVerbs::test_help_lists_refactor_and_narrative
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3115 (scope: src/frob/gates/_wire.py only, so this could not be fixed there). frob.__main__._dispatch routes 'refactor' and 'narrative' by a raw argv[0] scan before _build_parser() ever runs, and neither ever registers its add_refactor_parser/add_narrative_parser on the real _build_parser() tree -- only inside its own throwaway local parser built fresh per invocation. Consequence: frob --help never lists refactor or narrative as subcommands, even though both work when invoked directly (frob refactor --help exits 0 and shows move/rename/split/move-module; three tickets used frob refactor successfully on 2026-08-27). T-3115 worked around this for WIRE003's own purposes by resolving refactor/narrative's subcommand trees against their real add_*_parser functions directly, bypassing _build_parser -- but frob --help itself still will not show them. Fix: register add_refactor_parser(sub)/add_narrative_parser(sub) inside _build_parser() (in _add_analysis_subparsers or a similar group) purely for --help/discoverability, without changing _dispatch's existing raw-argv routing for actual execution (frob refactor/frob narrative would still be intercepted before parser.parse_args ever runs the built tree, so this is additive, not a routing change). Verify frob --help lists both verbs afterward and that WIRE003 (T-3115) still passes with _wire003_live_verb_tokens's supplemental hidden-verb lookup either kept (harmless, now redundant) or simplified once the tree covers them natively.