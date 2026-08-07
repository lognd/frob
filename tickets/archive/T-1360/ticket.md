---
id: T-1360
title: 'Footgun detection: warn when a command failed or under-reported in a way that
  looks like success'
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: T-1344
tier: ticket
sprint: null
scope:
- src/frob/app/telemetry.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/app/doctor_runner.py
- docs/guides/agentic-time-profiling.md
- tests/test_telemetry.py
- tests/unit/test_doctor_runner_t1276.py
- src/frob/app/_config_external.py
- src/frob/_cli_parsers/_misc.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/telemetry.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: docs/modules/telemetry.md
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/telemetry.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/app.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/config.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_telemetry.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: 'Ticket named src/frob/telemetry.py and docs/modules/telemetry.md, neither
    of

    which exist. The real telemetry module is src/frob/app/telemetry.py

    (docs/guides/agentic-time-profiling.md#public-api). Footgun detection reads

    that same telemetry.jsonl stream, so it lives there; emission needs a hook

    at the one place every CLI invocation already funnels through

    (src/frob/app/app.py''s timed_call call site) and a reporting verb needs

    argparse/AppConfig wiring (src/frob/app/config.py, src/frob/app/

    doctor_runner.py) plus the doc file that actually exists for this module.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_telemetry.py::test_detect_footguns_flags_redundant_rerun
- tests/test_telemetry.py::test_detect_footguns_flags_fast_exit1
- tests/test_telemetry.py::test_detect_footguns_does_not_flag_fast_exit1_on_success
- tests/test_telemetry.py::test_detect_footguns_flags_repeated_failure_streak
- tests/test_telemetry.py::test_detect_footguns_respects_suppress_env
- tests/test_telemetry.py::test_detect_footguns_returns_empty_when_tips_disabled
- tests/test_telemetry.py::test_render_tips_json_is_parseable
- tests/test_telemetry.py::test_render_tips_empty_list_is_empty_string
- tests/test_telemetry.py::test_render_tips_human_readable_names_the_rule
- tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero
- tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures
- tests/test_telemetry.py::test_usage_report_counts_redundant_reruns
- tests/test_telemetry.py::test_usage_report_counts_fast_exit1
designated_repro_test: null
acceptance:
- text: given a command re-run at an identical tree_hash with identical args, when
    it completes, then a tip names the prior run and its timestamp
  evidence:
  - tests/test_telemetry.py::test_detect_footguns_flags_redundant_rerun
  - tests/test_telemetry.py::test_detect_footguns_flags_fast_exit1
  - tests/test_telemetry.py::test_detect_footguns_does_not_flag_fast_exit1_on_success
  - tests/test_telemetry.py::test_detect_footguns_flags_repeated_failure_streak
  - tests/test_telemetry.py::test_detect_footguns_respects_suppress_env
  - tests/test_telemetry.py::test_detect_footguns_returns_empty_when_tips_disabled
  - tests/test_telemetry.py::test_render_tips_json_is_parseable
  - tests/test_telemetry.py::test_render_tips_empty_list_is_empty_string
  - tests/test_telemetry.py::test_render_tips_human_readable_names_the_rule
  - tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero
  - tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures
  - tests/test_telemetry.py::test_usage_report_counts_redundant_reruns
  - tests/test_telemetry.py::test_usage_report_counts_fast_exit1
- text: given a command that exits nonzero in under two seconds, when it completes,
    then a tip states plainly that it errored and did not do the work
  evidence:
  - tests/test_telemetry.py::test_detect_footguns_flags_fast_exit1
- text: given tips are emitted, when --json is requested, then they are machine-readable
    so an agent can self-correct
  evidence:
  - tests/test_telemetry.py::test_detect_footguns_flags_redundant_rerun
  - tests/test_telemetry.py::test_detect_footguns_flags_fast_exit1
  - tests/test_telemetry.py::test_detect_footguns_does_not_flag_fast_exit1_on_success
  - tests/test_telemetry.py::test_detect_footguns_flags_repeated_failure_streak
  - tests/test_telemetry.py::test_detect_footguns_respects_suppress_env
  - tests/test_telemetry.py::test_detect_footguns_returns_empty_when_tips_disabled
  - tests/test_telemetry.py::test_render_tips_json_is_parseable
  - tests/test_telemetry.py::test_render_tips_empty_list_is_empty_string
  - tests/test_telemetry.py::test_render_tips_human_readable_names_the_rule
  - tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero
  - tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures
  - tests/test_telemetry.py::test_usage_report_counts_redundant_reruns
  - tests/test_telemetry.py::test_usage_report_counts_fast_exit1
threat: null
component: telemetry
---
Leaf of T-1344. User request 2026-07-31: "Can we do a footgun protection? Can we detect when we are using frob tooling poorly?"

THE TARGET IS SHARPER THAN "POOR USAGE". One session produced THREE instances of a single family: an operation that fails or under-reports in a way INDISTINGUISHABLE FROM SUCCESS.
1. T-1293: coverage measured with the wrong denominator (scoped pytest --cov instead of the repo-wide stamp) -> agent closed a 64-finding ticket having fixed 1, reporting the package clean.
2. T-1337: verification run as `check --only opaque --ticket T-1337` -- filtered by gate AND scope -- so two INV006 errors were invisible and shipped to main.
3. Coordinator: timed `check --ticket T-XXXX` at 0.77s vs 139.7s unscoped and reported a 180x speedup. The fast runs were EXITING EARLY on "no recorded lease" -- an error path read as a speedup, then acted on and broadcast to three agents before being caught.
Three independent, competent actors hit the same shape in one day. That is a tooling defect, not a discipline problem.

THE SUBSTRATE ALREADY EXISTS: .frob/telemetry.jsonl, 12,300 records, fields args_head / duration_ms / exit / iso_ts / kind / subcommand / tree_hash. No new instrumentation is needed for the first rule set. tree_hash is the key field -- it makes redundancy PROVABLE rather than heuristic.

DETECTOR RULES, seeded from mining that corpus (not from a guessed list):
1. REDUNDANT RE-RUN: identical args_head at identical tree_hash. Measured 2.55 h of provably-wasted wall-clock; bare `check` alone repeated 39 times for 45.8 min. Tip: "you ran this exact command at this exact tree state N minutes ago; nothing has changed since."
2. FAST EXIT-1: low duration_ms with nonzero exit. 756 such runs in the corpus. This is the trap the coordinator hit -- the tip must say plainly "this exited with an ERROR in 0.5s; it did not do the work you may think it did."
3. FILTERED VERIFICATION BEFORE LAND: a --ticket or --only run as the last check preceding `ticket land`. This is exactly how T-1337 shipped errors. Must state what the filter SUPPRESSED, not merely that a filter was active (this subsumes/overlaps T-1351 -- reconcile, do not duplicate).
4. REPEATED IDENTICAL FAILURE: same command failing the same way N times = stuck, not progressing. Overall corpus failure rate is 11% (1351/12304); `ticket land` alone fails 36% of the time.
5. COVERAGE-NUMBER MISUSE: a coverage/TEST005 claim made against a stamp older than the working tree. Ties to T-1335.

DELIVERY REQUIREMENTS:
- A tip printed AFTER the command, never blocking it, rate-limited, individually suppressible (a tip that nags gets ignored, which is worse than no tip).
- MACHINE-READABLE form (--json or a structured stream) so AGENTS self-correct. Agents are now the primary users of this CLI and they cannot read a human-styled hint reliably. This is the difference between a nicety and the thing that actually stops the failure class.
- Every tip must name the concrete better command, not just diagnose. "Use --ticket" is useless; "you already ran this at tree_hash abc1234 8 minutes ago" is actionable.
- A `frob doctor usage`-style verb that reports YOUR top time sinks and footguns from the local corpus. The corpus answered "where does the time go" in minutes today; that capability should be a command, not an ad-hoc python script.

DO NOT: make tips block or fail a command; add a tip whose advice is unmeasured (the coordinator's 180x claim would have become a permanent false hint had it shipped into `brief`); or duplicate T-1351 -- fold rule 3 into whichever ticket implements it.