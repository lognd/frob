---
id: T-4689
title: Telemetry records the verb and subverb of every frob invocation (91% of rows
  carry none today)
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4687
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/tool-call-telemetry.py
- src/frob/app/telemetry/**
- tests/unit/test_telemetry_verb_recording.py
- src/frob/app/app.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/app.py
  reason: record_cli_event/timed_call call site lives in app.py's App.__call__, not
    __main__.py; needed to compute and pass subverb per T-4689
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2411
  new_length: 2411
evidence:
- tests/unit/test_telemetry_verb_recording.py::TestAppDispatchRecordsSubverb::test_ticket_show_records_verb_ticket_subverb_show
- tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_uv_run_frob
- tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_dot_venv_bin_frob
- tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_python_dash_m_frob
- tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_nice_wrapped_frob
- tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_compound_command_several_frob_calls
- tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_non_frob_bash_command_records_neither
designated_repro_test: null
acceptance:
- text: Given a fixture telemetry root, when frob ticket show T-xxxx runs, then the
    appended .frob/telemetry.jsonl row carries verb=ticket and subverb=show
  evidence:
  - tests/unit/test_telemetry_verb_recording.py::TestAppDispatchRecordsSubverb::test_ticket_show_records_verb_ticket_subverb_show
- text: Given a kind=tool hook payload whose Bash command invokes frob, when the hook
    records it, then the row carries the same verb/subverb fields; a non-frob Bash
    command records neither rather than a guess
  evidence:
  - tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_uv_run_frob
  - tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_dot_venv_bin_frob
  - tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_python_dash_m_frob
  - tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_nice_wrapped_frob
  - tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_compound_command_several_frob_calls
  - tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_non_frob_bash_command_records_neither
threat: null
component: cli
labels:
- cli-debloat
- points-2
anchor: false
anchor_reason: null
land_commit: null
---
POINTS: 2. Parent story T-4687. No blockers -- this leaf is file-disjoint from
every other leaf in the story and can start immediately.

PROBLEM, MEASURED 2026-09-19: .frob/telemetry.jsonl has 34388 rows and 31418 of
them (91%) carry an empty `subcommand`. Every kind=tool row is empty: those rows
are written by .claude/hooks/tool-call-telemetry.py from the Claude Code Bash
tool payload, and the hook never parses the frob verb out of the command line it
records. kind=cli rows (2970) do carry a verb, but only the FIRST word -- there
is no subverb, so `frob ticket show` and `frob ticket land` are both just
"ticket" (ticket alone accounts for 2165 of 2970 cli rows, so the whole of the
interesting distribution is collapsed into one bucket).

CONSEQUENCE: the tail of the 51 top-level verbs and 54 ticket subverbs cannot be
ranked from data. The rest of this story (T-4690..T-4698) deletes names on the
strength of `git grep` citation counts instead. This leaf makes the NEXT round
of pruning data-driven, and gives the sunset shims a way to prove nobody is
still calling the deprecated spelling.

WORK:
1. kind=cli path (src/frob/app/telemetry/__init__.py): record `verb` and
   `subverb` as separate fields, derived from the parsed argparse namespace
   (the dest the parser already sets -- `explore_command`, `quality_command`,
   `ticket_command`, `perf_command`, ...), NOT by re-lexing sys.argv. Keep
   `subcommand` populated for back-compat with the existing readers in
   src/frob/stats/_agentic*.py and app/telemetry/_footguns.py (footgun dedup
   keys on (subcommand, args_head) -- do not change that key's meaning without
   migrating the stored rows).
2. kind=tool path (.claude/hooks/tool-call-telemetry.py): when the recorded tool
   is Bash and the command invokes frob, extract verb and subverb into the same
   two fields. Be conservative: a command that does not resolve to a frob
   invocation records nothing rather than a guess.
3. Log every classification decision at DEBUG, and log at INFO when a frob-
   looking command could not be classified -- an unclassified row is the exact
   silent-zero this ticket exists to remove.

DO NOT: add a new verb for reading this. `frob stats` already reads the stream.

FILES (declared scope, disjoint from every other leaf):
  .claude/hooks/tool-call-telemetry.py
  src/frob/app/telemetry/**
  tests/unit/test_telemetry_verb_recording.py (new)