---
id: T-0202
title: 'frob check default output: stats summary, gate chatter to DEBUG, standardized
  log format'
state: done
kind: ux
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/logging/**
- src/frob/app/**
- src/frob/check/**
- src/frob/graph/**
- src/frob/gates/**
- src/frob/__main__.py
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_logging_quiet.py::TestStdoutLogLevel::test_sets_and_restores_arbitrary_level
- tests/unit/test_logging_quiet.py::TestStdoutLogLevel::test_restores_on_exception
- tests/system/test_cli_check.py::TestCheckVerbosity::test_default_has_no_dispatch_or_digest_lines
- tests/system/test_cli_check.py::TestCheckVerbosity::test_verbose_restores_dispatch_and_parse_lines
designated_repro_test: null
threat: null
component: null
---
Scope note (implementer, this pass): added `src/frob/__main__.py` -- the
`-v`/`-vv` flag this ticket requires can only be registered where argparse
lives, which is this file, not under `src/frob/app/**`. SCOPE001 flagged the
edit under the original scope list; extending scope here per the playbook's
sanctioned path rather than filing a separate blocking ticket for one
mechanical `add_argument` call.

User report 2026-07-18: default frob check output is ~6K lines, mostly per-file/per-symbol debug chatter ('dispatching path=... to grammar=python', 'extracted 17 symbols...', 'digested TestGrammarRoundTrip: sig=... body=...', per-gate run_gates timing lines). These are DEBUG-level diagnostics printed at default verbosity. Fix: (1) audit every log call in graph build/digest/dispatch/gate-run paths and set honest levels -- per-file and per-symbol lines to DEBUG, per-stage one-line summaries to INFO; (2) default (non-verbose) output = the tool summary table plus violations only; -v restores current firehose, -vv adds true debug; (3) standardize the logging format across all modules per ~/.claude/refs/logging.md conventions (module logger + one formatter -- no mixed bare-print/log styles between gates, graph, vet, sys); (4) keep --json machine output untouched and clean (quiet_stdout_logs already guards it -- extend coverage if any new chatter leaks). Acceptance: default frob check on this repo emits under ~200 lines; every line above INFO is actionable.