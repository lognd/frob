---
id: T-2979
title: 'Default output is debug spam: gitio/process spawn traces drown the result
  on nearly every command'
state: done
kind: ux
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/logging/**
- src/frob/__main__.py
- docs/modules/logging.md
- tests/unit/test_logging_module.py
- tests/unit/test_main_entry.py
- src/frob/app/doctor_runner.py
- tests/unit/test_doctor_runner_t1276.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/logging/**
  reason: relevel gitio/process spawn traces from default stdout to DEBUG-gated
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/__main__.py
  reason: relevel gitio/process spawn traces from default stdout to DEBUG-gated
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/logging.md
  reason: relevel gitio/process spawn traces from default stdout to DEBUG-gated
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_logging_module.py
  reason: relevel gitio/process spawn traces from default stdout to DEBUG-gated
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: relevel gitio/process spawn traces from default stdout to DEBUG-gated
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: doctor plain path never wrapped run_diagnosis() in quiet_stdout_logs like
    its json/usage siblings do
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: doctor plain path never wrapped run_diagnosis() in quiet_stdout_logs like
    its json/usage siblings do
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_no_flag_or_env_var_is_none
- tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_dash_v_in_argv_is_debug
- tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_dash_dash_verbose_in_argv_is_debug
- tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_frob_verbose_env_var_is_debug
- tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_frob_log_level_env_var_is_parsed
- tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_unrecognized_frob_log_level_is_none_not_a_crash
- tests/unit/test_logging_module.py::test_config_toml_stdout_default_level_is_info_not_debug
- tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_v_sets_debug_env_var
- tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_dash_verbose_sets_debug_env_var
- tests/unit/test_main_entry.py::TestVerboseFlag::test_no_verbose_flag_leaves_env_var_untouched
- tests/unit/test_main_entry.py::TestVerboseFlag::test_existing_explicit_frob_log_level_is_not_clobbered
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerPlainPathQuieted::test_plain_path_raises_stdout_handlers_to_warning_by_default
- tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerPlainPathQuieted::test_plain_path_leaves_stdout_handlers_alone_under_frob_verbose
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 50850d8a1b7b407f9dab685128ce7be0a3c5063b
---
`frob doctor` (and most other frob commands) emit internal diagnostic logging
to the terminal at default verbosity. Observed repeatedly this session on
ordinary invocations:

    gitio: spawning ('git', '-C', '.', 'rev-parse', '--abbrev-ref', 'HEAD') (cwd=None, timeout=30s)
    process: spawning ['git', '-C', '.', 'rev-parse', '--abbrev-ref', 'HEAD']
    gitio: ('git', '-C', '.', 'rev-parse', '--abbrev-ref', 'HEAD') -> returncode=0
    tickets: v2 index cache hit (132 ticket(s))
    is_baseline_stale: frob-core/src/lib.rs changed since stamp

Three lines per git subprocess, and frob shells out to git constantly. The
signal-to-noise ratio is bad enough that this session routinely piped frob
output through `grep -viE "^(gitio|process|tickets:)"` just to read a result --
which is itself a hazard, since grepping a command's output to make it legible
is how a real error gets filtered away unseen.

This is a default-verbosity problem, not a logging-design problem: the repo's
logging setup (module logger + dictConfig, per the house logging reference) is
correct, and the standing engineering rule is LOG EVERYTHING WORTH LOGGING --
so the fix is NOT to delete these lines. They belong at DEBUG, reachable with
a flag or env var, not on stdout by default.

WHAT IS WANTED
- Default interactive output shows the command's RESULT plus genuine warnings
  and errors. Subprocess-spawn traces, cache-hit notices and staleness probes
  move to DEBUG.
- A documented way to get them back (`-v`/`--verbose`/`FROB_LOG_LEVEL=DEBUG`)
  -- and whichever it is, it must appear in `--help`.
- Warnings and errors keep their current prominence. Do not quiet the
  `[FAST_EXIT1]`/`[REDUNDANT_RERUN]`/`[REPEATED_FAILURE]` diagnostics or gate
  findings; those earn their place and caught real mistakes this session.

CONSTRAINTS
- Route through the existing single logging configuration. Do not add a second
  verbosity mechanism beside it.
- `--json` and other machine paths must stay byte-identical. Prove with a diff.
- Apply repo-wide, not just to `doctor` -- doctor is where it was noticed, but
  `gitio`/`process` spam appears on nearly every command.

ACCEPTANCE
- Given a default `frob doctor` run on a TTY, when it completes, then no
  `gitio:`/`process:` spawn traces or cache-hit notices appear, and the
  diagnostic result is legible without piping through grep.
- Given `-v` (or the documented equivalent), when the same command runs, then
  those lines reappear in full -- nothing was deleted, only re-levelled.
- Given a warning or error condition, when it occurs at default verbosity,
  then it is still shown. Must-still-show fixture required.
- Given `--json`, when the command runs, then output is byte-identical to
  today.