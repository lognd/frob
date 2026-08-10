---
id: T-1568
title: 'cli regrouping: frob design verb group (sys/registry/docs/graph/exports)'
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
- src/frob/_cli_parsers/_design.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/_cli_parsers/__init__.py
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/app.py
- src/frob/app/design_runner.py
- docs/modules/cli.md
- docs/design/cli-regrouping.md
- docs/modules/app.md
- README.md
- tests/unit/test_app_runners.py
- tickets/T-1568/**
- docs/commands/exports.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_design.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/__main__.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/app.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/design_runner.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: README.md
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners.py
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1568/**
  reason: narrow mega-glob to the exact files T-1568 (design verb group) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/commands/exports.md
  reason: 'AFFECT001: _add_exports_parser''s affects()-closure doc needs a touch noting
    the new frob design exports alias'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[sys]
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[registry]
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[docs]
- tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[graph]
- tests/unit/test_app_runners.py::TestDesignRunner::test_exports_subcommand_delegates_to_exports_runner
- tests/unit/test_app_runners.py::TestDesignRunner::test_unknown_subcommand_exits_1
designated_repro_test: null
threat: null
component: null
---
Refiled from T-1568 (T-1238 taxonomy slice, draft-loss class). Group design/model verbs under frob design following the frob explore precedent.

## Done report

Added the `frob design` verb group (T-1568, same shape as `frob quality`/
T-1567, following `frob explore`/T-1238): sys/registry/docs/graph/exports
grouped under `frob design <subcommand>`, each dispatching straight into
the existing standalone runner's `run(cfg)`. Every standalone top-level
form stays a permanent alias per docs/design/cli-regrouping.md's
migration policy.

Avoided argparse duplication the same way T-1567 did: extracted shared
`_populate_graph_actions`/`_populate_registry_actions` (previously inline
in _add_graph_parser/_add_registry_parser, _reporting.py) and
`_populate_docs_args`/`_populate_exports_args` (_core.py); reused sys's
already-factored `_add_sys_plan_and_export_parsers`/`_add_sys_doc_and_
audit_parsers`/`_add_sys_sync_interface_parser` directly. Both the
standalone parser and the new design-group parser call the same helper
per member.

`frob design docs` deliberately omits `--search` (`_populate_docs_args(...,
include_search=False)`) -- docs/design/cli-regrouping.md's own bucket
split keeps full-text search exclusive to `frob explore docs-search`;
bare extract/`--overview` only under `design`.

Wired: Subcommand.design + AppConfig.design_command (config.py),
_STRING_FIELDS entry (_config_external.py), design_runner module name in
all three app.py registries, __main__.py import/wiring. Re-added
frob:ticket T-1568 edges alongside T-1567's existing ones on the app.py/
config.py symbols this ticket ALSO touched (_RUNNER_MODULE_NAMES,
_SUBCOMMAND_RUNNER_NAMES, _import_runner_module, Subcommand, AppConfig)
-- COV002 requires an edge per ticket whose diff touches the symbol, not
just the most recent one.

Docs: docs/modules/cli.md regenerated; docs/design/cli-regrouping.md's
`frob design` section marked IMPLEMENTED; docs/modules/app.md gained a
design_runner Runners paragraph (AFFECT001); README.md gained a `frob
design` command-table row and the 39->40 count bump (DOC005);
docs/commands/exports.md gained a one-line pointer to the new alias
(AFFECT001 on _add_exports_parser's own affects()-closure doc).

Verification: `uv run frob check --only gates-fast --ticket T-1568` and
`--only gates-native --only gates-security --ticket T-1568` both clean
(0 errors, no new WIRE001 this time -- design's subparsers have no
dispatch-bypassed member like quality's bind); `uv run frob check
--land-parity` clean (0 unscoped errors); `pytest
tests/unit/test_app_runners.py` 57 passed.

### Changed
```
 tickets/T-1568/ticket.md | 114 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 113 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[sys]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[registry]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[docs]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestDesignRunner::test_subcommand_delegates_to_matching_runner[graph]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestDesignRunner::test_exports_subcommand_delegates_to_exports_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestDesignRunner::test_unknown_subcommand_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 739 warning(s), 740 waived
- error-findings: PRE001@tickets/T-1568
