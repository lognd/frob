---
id: T-0940
title: 'main red: T-0715 DRIFT002 test-edge resolution x12 + PARSE002 on intentional
  broken.py fixture'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/__init__.py
- tests/unit/test_app_runners_t0715_sprint_tier.py
- tests/fixtures/lang/broken.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestErrors::test_syntax_error_yields_partial_symbols
- tests/test_gates.py::TestParseFailureGate::test_partial_parse_is_an_error_violation
- tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketNewTierSprint::test_new_carries_tier_and_sprint
- tests/test_tickets_tiers.py::TestTierField::test_default_tier_is_ticket
designated_repro_test: null
acceptance:
- text: given current main plus this fix, when uv run frob check runs cleanly rebuilt,
    then gate-summary reports 0 errors
  evidence:
  - tests/test_lang.py::TestErrors::test_syntax_error_yields_partial_symbols
  - tests/test_gates.py::TestParseFailureGate::test_partial_parse_is_an_error_violation
  - tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketNewTierSprint::test_new_carries_tier_and_sprint
  - tests/test_tickets_tiers.py::TestTierField::test_default_tier_is_ticket
threat: null
component: null
---
Main sits at 13-15 gate errors after the T-0715 and T-0902/T-0905 lands. (1) 12x DRIFT002: every T-0715 frob:tests edge (5 in the new tests/unit/test_app_runners_t0715_sprint_tier.py, 7 in src/frob/tickets/{_models,__init__}.py) reports 'no longer resolves; candidates: no candidates found' -- persists after deleting .frob/pytest-collect.json and re-running check, so likely the DRIFT gate resolves against the obligation graph rather than the pytest collect cache and the graph needs a rebuild, OR the new-file edges were recorded in a form the resolver cannot match (compare against directives that DO resolve, e.g. the dotted Class.method edges elsewhere in _models.py). Diagnose properly, fix the edges or the cache, do NOT bulk-rewrite directives (a coordinator sed attempt over-matched -- reverted). (2) 1x PARSE002 on tests/fixtures/lang/broken.py, the intentionally-malformed parser fixture -- the gate's own message endorses an in-file frob:waive PARSE002 with a reason; verify the waive parses in a file with a syntax error and does not perturb fixture-position-sensitive tests (tests/test_lang.py, test_gates.py::TestParseFailureGate, test_graph.py), else exclude fixtures from PARSE002 the same way T-0897 excluded graph-excluded paths from PII010/RENDER001/SEC scans. Zero gate errors on main is the acceptance bar.