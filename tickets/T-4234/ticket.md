---
id: T-4234
title: the scaffold end-to-end test hardcodes the posix virtualenv script directory,
  so it cannot pass on Windows
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_scaffold_dx.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the scaffold end-to-end test running on any supported platform, when
    it looks for the generated console script, then it finds and runs it
  evidence: []
- text: given the posix platform, when the test runs, then its behaviour is unchanged
    from today
  evidence: []
- text: given the console-script path, when it is computed, then it is derived from
    the environment's install scheme rather than a hardcoded directory name
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A TEST WE ADDED TODAY HARDCODES THE POSIX VIRTUALENV LAYOUT AND THEREFORE CANNOT
PASS ON WINDOWS. This is our own regression, introduced by T-3930's acceptance
test, and it is a NEW Windows failure that did not exist in the previous run.

    tests/system/test_scaffold_dx.py
      ::test_hyphenated_name_scaffold_installs_and_console_script_runs
    "console-script entry point was not installed"
    looked for: <project>/.venv/bin/my-test-tool

The assertion is at tests/system/test_scaffold_dx.py:303:

    script = project_dir / ".venv" / "bin" / "my-test-tool"

A virtual environment places console scripts in a `bin` directory on posix and a
`Scripts` directory on Windows, and the file carries an executable suffix there.
So the path can never exist on Windows and the test fails by construction, no
matter how correct the scaffold is.

THE IRONY IS WORTH RECORDING BECAUSE IT IS THE LESSON. T-3930 fixed a defect whose
root cause was a project-name assumption baked into generated code, and verified
it by scaffolding, installing and running the console script end to end. That
verification is exactly right and should be kept. But the verification itself
baked in a PLATFORM assumption, so the test that proves the scaffold works
everywhere only runs where its author was standing. This repository has now
produced that shape three times in one day: a fixture asserting a Windows path
behaviour reasoned out on linux, a replacement fixture asserting a new library's
behaviour the same way, and now an acceptance test asserting a posix install
layout.

THE FIX IS SMALL AND SHOULD NOT BE A CONDITIONAL IF SOMETHING BETTER EXISTS. Ask
the environment where its scripts live rather than assembling the path by hand --
the standard library exposes the install scheme, and a virtualenv's own layout is
discoverable. A hand-written platform branch is the fallback, not the first
choice, because it is the same class of assumption one level up.

CHECK FOR SIBLINGS IN THE SAME FILE AND ITS NEIGHBOURS. This test was added
alongside a whole end-to-end scaffold verification; if any other step assembles a
path into the generated project's environment by hand, it has the same defect and
is only passing because nothing has run it on Windows yet.

NOTE ON THE SURROUNDING RUN, so nobody misreads the CI evidence: the Windows leg
that surfaced this ABORTED with an internal scheduler error partway through and
reported its failing set as incomplete, with a worker also dying at the
five-minute mark under suspected memory pressure. So this finding is real, but
the run it came from is not a measurement of the Windows failure count and must
not be treated as one.

MUST-FIRE FIXTURE:   the scaffold end-to-end test locates and runs the generated
                     console script on the platform it is running on.
MUST-STAY-QUIET:     the posix behaviour is unchanged -- the script is still
                     located and executed there exactly as today.
THIRD FIXTURE:       the path is derived from the environment's own install
                     scheme rather than assembled from a hardcoded directory name.

ACCEPTANCE
- The console-script path derived rather than hardcoded, with a platform branch
  used only if no derivation is available and the reason recorded.
- Sibling steps in the same end-to-end test audited for the same assumption.
- No weakening of the end-to-end verification itself; it stays a real install and
  a real invocation.
- All three fixtures committed.
