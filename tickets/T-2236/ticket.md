---
id: T-2236
title: Documented invocation of coordinator scripts (bare python3) violates requires-python
  >=3.11, and the failure is a raw ImportError -- broke fleet_status the minute a
  legal 3.11 feature landed
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- scripts/frob-telemetry-hook
- docs/guides/coordinator-scripts.md
- tests/unit/test_require_python.py
- scripts/_require_python.py
- tests/unit/conftest.py
- tests/unit/test_coordinator_scripts.py
evidence_scope:
- tests/unit/test_require_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_require_python.py
  reason: new repro/regression test for the interpreter-version guard
  actor: logan
  at: '2026-08-17'
- op: add
  glob: scripts/_require_python.py
  reason: the new shared version-guard module; scope already lists fleet_status.py/frob-telemetry-hook
    which import it
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/conftest.py
  reason: DUP001 fix shared/updated the _load helper in both files
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: DUP001 fix shared/updated the _load helper in both files
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
designated_repro_test: tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
acceptance:
- text: Running under an interpreter older than requires-python prints an actionable
    message (required version, found version, correct command) and exits non-zero
    without a raw ImportError traceback
  evidence:
  - tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
- text: The guard reads the requirement from a single source of truth, not a hardcoded
    (3,11) duplicated per script; if that needs a dependency these import-light scripts
    cannot take, propose the minimal alternative
  evidence:
  - tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
- text: 'MUST-STILL-PASS: under a supported interpreter every script''s output is
    byte-identical before and after -- the guard is invisible on the happy path'
  evidence:
  - tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
- text: docs/guides/coordinator-scripts.md documents the invocation actually guaranteed
    to work
  evidence:
  - tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
- text: Both affected scripts covered; any other version-sensitive script under scripts/
    is reported, not silently fixed
  evidence:
  - tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 44f5e684fee971d6e4edc487d4ebf6763f2f0e27
---
# The documented way to run the coordinator scripts violates the project's own `requires-python`, and the failure is a raw ImportError

## Measured evidence (2026-08-16)

T-2222 landed and `scripts/fleet_status.py` -- the coordinator's primary
instrument -- stopped working within a minute:

    $ python3 scripts/fleet_status.py
    Traceback (most recent call last):
      File "scripts/fleet_status.py", line 35, in <module>
        from datetime import UTC, date, datetime
    ImportError: cannot import name 'UTC' from 'datetime'
                 (/usr/lib/python3.10/datetime.py)

    $ python3 -VV
    Python 3.10.12

**The landed code is CORRECT.** `pyproject.toml` declares
`requires-python = ">=3.11"`, and `datetime.UTC` is a legitimate 3.11 feature.
T-2222 did nothing wrong. Under the venv it works:

    $ uv run python scripts/fleet_status.py
    ROOT CLEAN ...

**The defect is the documented invocation.** `docs/guides/coordinator-scripts.md`
tells the operator to run `python3 scripts/fleet_status.py`. Bare `python3` is
whatever the machine provides -- here 3.10.12 -- so the documented command is
not guaranteed to satisfy the project's own declared minimum. The moment
anyone legitimately used a 3.11 feature, the documented path broke.

Exposure is not limited to one file: `scripts/frob-telemetry-hook` also
imports `UTC`. Measured: **no script under `scripts/` guards its interpreter
version at all** (`git grep -nE "version_info" -- scripts/` returns nothing).

## Why this is a repeat, not a one-off

This is the same shape as an already-recorded footgun: "bare `frob` on PATH is
the stale global tool; ALWAYS `uv run frob`." The rule was learned for the
`frob` binary and never generalised to the interpreter. A written rule that
covers one binary and not the obviously-analogous other is not enforcement --
which is why this recurred with `python3`.

## Do NOT fix it this way

- **Do NOT rewrite the code to avoid `datetime.UTC`** (e.g. back to
  `timezone.utc`) to keep 3.10 working. The project REQUIRES >=3.11. Coding to
  an unsupported-but-installed interpreter means every future 3.11 feature is
  a latent landmine, and it silently redefines the support floor without
  changing `requires-python`.
- **Do NOT fix only the docs.** Correcting the guide leaves the raw traceback
  as the failure mode for anyone whose `python3` is older -- including a fresh
  clone, a CI runner, or an operator following muscle memory. The script
  should say what is wrong.
- **Do NOT lower `requires-python` to 3.10.** That is a real support-matrix
  decision, not a fix for a doc bug, and nothing here justifies it.
- **Do NOT add a `#!/usr/bin/env python3.11` shebang and call it done.** These
  are invoked as `python3 <script>`, so the shebang is bypassed entirely.

## Acceptance criteria

1. (MUST FAIL FIRST) Running the script under an interpreter older than the
   declared `requires-python` prints a clear, actionable message naming the
   required version, the version found, and the correct command
   (`uv run python scripts/...`) -- and exits non-zero WITHOUT a raw
   ImportError traceback. Fails today: bare ImportError from line 35.
2. The guard reads the requirement from a single source of truth rather than
   hardcoding `(3, 11)` in each script. If `requires-python` cannot be read
   without adding a dependency (these scripts are deliberately import-light --
   see fleet_status.py's own comment near line 97), say so and propose the
   minimal alternative rather than silently duplicating the constant.
3. MUST-STILL-PASS CONTROL: under a supported interpreter, every script's
   current behaviour and output is unchanged -- the guard must be invisible on
   the happy path. Verify `uv run python scripts/fleet_status.py` output is
   byte-identical before and after.
4. `docs/guides/coordinator-scripts.md` documents the invocation that is
   actually guaranteed to work.
5. Both affected scripts are covered (`scripts/fleet_status.py`,
   `scripts/frob-telemetry-hook`). If others under `scripts/` use
   version-sensitive features, report them rather than fixing silently.

## Scope note

This is a guard-and-docs fix. Do not refactor the scripts' logic while here.