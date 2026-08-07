---
id: T-0107
title: Wire frob check --stamp-baseline/--delta CLI flags and docs
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/app/check_runner.py
- src/frob/app/config.py
- docs/modules/gates.md
- docs/commands/check.md
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_stamp_baseline_writes_stamp
- tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation
designated_repro_test: null
threat: null
component: null
---
T-0095 added frob.gates.stamp_baseline/load_baseline/is_baseline_stale/delta_violations and threaded delta through run_check, but the --stamp-baseline/--delta CLI flags and docs remain unwired (outside T-0095 scope). Mirror --stamp-coverage's wiring in check_runner.py; document the agent-workflow motivation in docs/modules/gates.md + docs/commands/check.md. (Renumbered from branch-local T-0104 at merge.)
## Done report

Wired --stamp-baseline and --delta onto frob check, exposing T-0095's
baseline machinery: stamp runs the gates stage undelta'd, writes
.frob/baseline via gates.stamp_baseline, and exits; --delta threads
through run_check and filters only the gates stage, falling back to the
full set with a warning when the baseline is missing or stale.
AppConfig gains check_stamp_baseline/check_delta (scope widened to
config.py, recorded). docs/commands/check.md and docs/modules/gates.md
document both flags and anchor the five baseline symbols. Reviewer
APPROVED; noted non-blocking: combined --stamp-baseline --delta follows
the --stamp-coverage precedent (stamp wins, delta ignored). Verified on
main post-merge: 19 system tests in test_cli_check.py pass; frob check
exit 0 at the fresh baseline.