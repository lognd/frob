---
id: T-2582
title: 'human-mode query commands drown their answer in DEBUG chatter: xref emits
  5958 lines for a 13-line result'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/logging/quiet.py
- src/frob/app/debt_runner.py
- src/frob/app/deprecated_runner.py
- src/frob/app/exports_runner.py
- src/frob/app/fleet_runner.py
- src/frob/app/gitlog_runner.py
- src/frob/app/mutate_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- docs/modules/logging.md
- docs/modules/app.md
evidence_scope:
- tests/unit/test_logging_quiet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/logging/quiet.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/debt_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/deprecated_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/exports_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/fleet_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/gitlog_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/mutate_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/outline_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/xref_runner.py
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/logging.md
  reason: 'Stream-split fix: quiet stdout by default for the 8 human-mode query

    runners drowned in DEBUG chatter, sharing one new helper in quiet.py

    (FROB_VERBOSE=1 env-var opt-out) instead of 8 per-site edits. Avoids

    config.py/_config_external.py/CLI-parser fields (T-2574 holds a live

    lease on _config_external.py) by using an env var rather than a new

    per-command --verbose flag, matching the ticket''s own "or an env var"

    allowance. docs/modules/logging.md documents the new public symbol.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/app.md
  reason: 'AFFECT001: the 6 touched runners affects()-close to docs/modules/app.md#runners'
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_logging_quiet.py::TestQuietQueryStdout::test_quiets_by_default
- tests/unit/test_logging_quiet.py::TestQuietQueryStdout::test_frob_verbose_env_var_restores_full_chatter
- tests/unit/test_logging_quiet.py::TestQuietQueryStdout::test_restores_on_exception
designated_repro_test: tests/unit/test_logging_quiet.py::TestQuietQueryStdout::test_quiets_by_default
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 62007fc8d8e1e0e93511234884ba5ff2a12448e2
---
## Symptom

Agents are abandoning `frob explore xref` and falling back to raw `grep`,
despite a hook that actively recommends xref over grep. The tool is not
broken -- it is unreadable.

## Measured

    frob xref _doable_sort_key            5958 stdout lines, answer at 5946
    frob xref _doable_sort_key --json       64 stdout lines, clean
    runtime                                ~27s either way

5943 of 5958 stdout lines (99.75%) are DEBUG/INFO parse chatter
(`gitio: spawning`, `dispatching path=`, `parse cache hit`, `extracted N
symbols`). The actual answer -- definition plus every use site, which is
CORRECT and genuinely useful -- is the last 13 lines.

## Root cause: one line, and the condition is backwards in effect

`src/frob/app/xref_runner.py:29`

    ctx = quiet_stdout_logs() if cfg.xref_json else contextlib.nullcontext()

Log quieting is applied ONLY in `--json` mode. The human path gets
`nullcontext()`. So the machine-readable path is protected and the human
path is abandoned -- backwards from what a human-facing command needs.

## This is repo-wide, not one command

Same `quiet_stdout_logs() if <cmd>_json else nullcontext()` pattern:

    app/debt_runner.py:60          app/gitlog_runner.py:39
    app/deprecated_runner.py:78    app/mutate_runner.py:42
    app/exports_runner.py:24,117   app/outline_runner.py:45
    app/fleet_runner.py:68         app/xref_runner.py:29

Every one of those human-facing query commands is drowned the same way.

NOTE: `_guard_json_stdout_writes()` (bind/check/clean/docs/fmt/graph/map
runners) is a DIFFERENT helper -- it guards stray writes from corrupting
JSON output and is legitimately json-only. Do not "fix" those.

## Why this is worse than cosmetic

The natural way to use a query tool is to bound its output:

    frob explore xref foo | head -20

which returns 20 lines of `gitio: spawning ...` and ZERO answer -- exactly
indistinguishable from a broken or empty tool. An agent then reasonably
concludes xref does not work and falls back to grep. This has been observed
happening. It is the same class as the recurring lesson that a truncated or
piped view can hide the real signal entirely.

It also actively burns agent context: 5958 lines per invocation, of which
13 matter.

## Fix

Quiet stdout-bound INFO/DEBUG for the HUMAN path too. The mechanism already
exists and needs no new machinery -- `frob.logging.quiet.quiet_stdout_logs`,
whose own docstring documents this exact problem ("root-logger stdout
handler defaults to DEBUG (config.toml), so every per-file/per-symbol
DEBUG/INFO log line prints at default verbosity").

Preferred shape: quiet by default in BOTH modes, with an explicit opt-in
(`-v`/`--verbose`, or an env var) to restore the chatter for debugging.
Diagnostics belong on stderr; the RESULT belongs on stdout. Today the
diagnostics are on stdout, mixed into the result -- that is the deeper
defect and fixing the stream split may be the cleaner fix than toggling
levels.

Apply across all eight runners listed above, not just xref. A per-site fix
leaves the ninth to be written next week -- prefer one shared helper or a
default that a runner opts OUT of.

## Positive controls, both directions

- human mode returns the answer within the first screenful, and `| head -20`
  shows real content
- `--json` output stays byte-identical and machine-parseable
- the opt-in verbose flag STILL produces the full diagnostic stream -- a fix
  that deletes the diagnostics rather than routing them is a regression, and
  those lines are load-bearing when debugging a parse problem

## Immediate workaround for agents (until this lands)

Use `--json`. It is clean at 64 lines and carries the same information.