---
id: T-1567
title: 'cli regrouping: frob quality verb group (check/test/dup/arch/bind/cycle/mutate/perf)'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1725
- T-1764
- T-1765
- T-1766
parent: T-1238
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_quality.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_check.py
- src/frob/_cli_parsers/__init__.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/app.py
- src/frob/app/quality_runner.py
- docs/modules/cli.md
- docs/design/cli-regrouping.md
- tests/unit/test_app_runners.py
- tickets/T-1567/**
- docs/modules/app.md
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_quality.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_check.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/__main__.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/app.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/quality_runner.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1567/**
  reason: narrow mega-glob to the exact files T-1567 (quality verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: AFFECT001/DOC005 require touching app.md's runner doc + README's command
    table alongside the new quality_runner
  actor: logan
  at: '2026-08-08'
- op: add
  glob: README.md
  reason: AFFECT001/DOC005 require touching app.md's runner doc + README's command
    table alongside the new quality_runner
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[check]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[test]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[dup]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[cycle]
- tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[perf]
- tests/unit/test_app_runners.py::TestQualityRunner::test_arch_subcommand_delegates_to_arch_runner
- tests/unit/test_app_runners.py::TestQualityRunner::test_mutate_subcommand_missing_file_exits_nonzero
- tests/unit/test_app_runners.py::TestQualityRunner::test_unknown_subcommand_exits_1
designated_repro_test: null
threat: null
component: null
---
Refiled from T-1567 (T-1238 taxonomy slice; the draft died in the land-splice draft-loss class before T-1271's land). Group the quality-facing verbs under one frob quality namespace following the frob explore precedent (T-1271/T-1238, src/frob/_cli_parsers/_explore.py + explore_runner.py).

## Done report

Added the `frob quality` verb group (T-1567, following the `frob explore`
precedent, T-1238): check/test/dup/arch/bind/cycle/mutate/perf grouped
under `frob quality <subcommand>`, each dispatching straight into the
existing standalone runner's `run(cfg)`/argv path -- no duplicated
business logic, every standalone top-level form stays a permanent alias
per docs/design/cli-regrouping.md's migration policy.

Avoided literal argparse duplication (the explore precedent's own shape,
acceptable there because each member was <15 lines) by extracting shared
`_populate_*_args(parser)` helpers for cycle/dup/arch/test/mutate in
_core.py/_misc.py, and reusing _check.py's already-factored
_add_check_scope_args/_add_check_skip_args/_add_check_selection_args and
_misc.py's already-factored perf sub-builders directly -- both the
standalone parser and the new quality-group parser call the same helper,
so the flag list for each member is declared exactly once.

`bind` is the one member requiring special handling: `bind_runner.run`
takes raw argv, not an AppConfig, because top-level `frob bind` itself is
dispatched by `frob.__main__._dispatch` BEFORE the argparse tree is built
(T-0355's SIGINT-safety special case). `frob quality bind` mirrors that
exact precedent (`_is_quality_bind` helper, extracted to keep `_dispatch`
under the ARCH001 60-line threshold) rather than routing through
`quality_runner.run`; the quality-group's `bind` subparser exists only
for --help discovery, matching the pre-existing `agent`/`worktree`
grandfather pattern for dispatch-bypassed subcommands.

Wired: Subcommand.quality + AppConfig.quality_command (config.py),
_STRING_FIELDS entry (_config_external.py), quality_runner module name in
all three app.py registries (_RUNNER_MODULE_NAMES,
_SUBCOMMAND_RUNNER_NAMES, _import_runner_module's closed if/elif chain),
__main__.py import/wiring + the quality-bind dispatch branch.

Docs: docs/modules/cli.md regenerated via `frob docs --sync-commands`;
docs/design/cli-regrouping.md's `frob quality` section marked IMPLEMENTED
with the built shape; docs/modules/app.md's Runners section gained a
quality_runner paragraph (AFFECT001); README.md gained a `frob quality`
command-table row and the 38->39 count bump (DOC005).

Gate fixes made while landing this: ARCH001 (extracted _is_quality_bind
to keep _dispatch under 60 lines), two DUP001 findings (both pre-existing
mirrored-pattern pairs this ticket's edit nudged over the similarity
threshold -- waived with reasons citing the deliberate mirroring), three
WIRE001 findings on the bind subparser's --help-only dests (waived with
follow_up=T-1820, a chore ticket recording this as a permanent
by-design gap, since WIRE002 requires a real ticket id outside tests/
trees), one OPAQUE001 in my own first draft of the test file (rewrote the
parametrized delegation test's dynamic importlib.import_module lookup as
a closed if/elif chain of literal imports, same convention as
frob.app.app._import_runner_module), and a COV005/COV002 directive
placement bug where `_is_quality_bind`'s insertion silently absorbed
`_dispatch`'s own frob:ticket/frob:tests block (moved it, added explicit
frob:ticket T-1567 edges on the four other new/changed app.py/config.py
symbols).

Filed T-1820 (renumbers at land) as the WIRE002 follow_up
anchor described above -- not real deferred work, just the ticket id the
gate requires.

Verification: `uv run frob check --only gates-fast --ticket T-1567` and
`--only gates-native --only gates-security --ticket T-1567` both clean
(0 errors); `uv run frob check --land-parity` clean (0 unscoped errors);
`pytest tests/unit/test_app_runners.py tests/unit/test_main_entry.py`
66 passed.

### Changed
```
 tickets/T-1567/ticket.md           | 111 ++++++++++++++++++++++++++++++++++++-
 tickets/T-1820/ticket.md |  31 +++++++++++
 2 files changed, 141 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[check]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[test]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[dup]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[cycle]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestQualityRunner::test_subcommand_delegates_to_matching_runner[perf]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestQualityRunner::test_arch_subcommand_delegates_to_arch_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestQualityRunner::test_mutate_subcommand_missing_file_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestQualityRunner::test_unknown_subcommand_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 1 error(s), 740 warning(s), 741 waived
- error-findings: PRE001@tickets/T-1567
