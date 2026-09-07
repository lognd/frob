---
id: T-3930
title: frob scaffold new with a hyphenated name generates an unimportable package
  and a failing generated test
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/**
- tests/system/test_scaffold_dx.py
- tests/unit/test_scaffold_project.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/**
  reason: fix hyphen-vs-import-name split across all scaffold templates and generated
    tests
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/system/test_scaffold_dx.py
  reason: fix hyphen-vs-import-name split across all scaffold templates and generated
    tests
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_scaffold_project.py
  reason: fix hyphen-vs-import-name split across all scaffold templates and generated
    tests
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/scaffold/**
  reason: fix hyphen-vs-import-name split across all scaffold templates and generated
    tests
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/system/test_scaffold_dx.py
  reason: fix hyphen-vs-import-name split across all scaffold templates and generated
    tests
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_scaffold_project.py
  reason: fix hyphen-vs-import-name split across all scaffold templates and generated
    tests
  actor: logan
  at: '2026-09-07'
body_changes:
- mode: set
  reason: 'reproduced on today''s main and upgraded the finding: the generated test
    file is a SyntaxError, so the scaffolded project''s suite cannot be COLLECTED
    rather than merely failing. Records that a fix touching only the package dir and
    console script would leave the generated test source unparseable, and that the
    fixture must run or parse the generated tests'
  actor: logan
  at: '2026-09-07'
  old_length: 3644
  new_length: 5858
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob scaffold new python-tool kicad-libsync` PRODUCES A PROJECT THAT CANNOT
IMPORT ITSELF. Reported by a fresh downstream consumer (kicad-libsync) on
frob 0.530.0, as the very first thing they did.

WHAT IT GENERATED:

    src/kicad-libsync/                                  <- hyphenated DIRECTORY
    [project.scripts]            kicad-libsync.__main__:main
    [tool.setuptools.package-data]  kicad-libsync = [...]
    tests/system/test_build.py   importlib.import_module("kicad-libsync")

NONE OF THOSE ARE VALID PYTHON NAMES. A hyphen cannot appear in a module or
package identifier, so the generated package is unimportable, the console-script
entry point cannot resolve, and the scaffold's OWN generated test fails. The
consumer fixed it by hand with `mv` plus `sed` before their first commit.

THE CORRECT BEHAVIOUR IS WELL-ESTABLISHED AND UNAMBIGUOUS: a distribution name
may contain hyphens (PyPI convention, and `kicad-libsync` is the right
DISTRIBUTION name); the IMPORT name must be the underscored form. So the
scaffold should derive `kicad_libsync` for the package directory and every
dotted reference, while keeping `kicad-libsync` for the PyPI name and the
console-script name. That split is standard packaging practice, not a judgement
call.

WHY THIS IS THE MOST SEVERE FINDING FOR THE ALPHA, ahead of anything else in
the queue:

  1. IT IS THE FIRST COMMAND A NEW USER RUNS. `frob scaffold new` is the
     entry point to the entire tool. A user whose first action produces a
     broken project does not file a ticket; they stop.
  2. IT AFFECTS THE NORMAL CASE, NOT AN EDGE CASE. Multi-word project names
     are the majority of real projects, and hyphenation is the PyPI
     convention for them. `frob-core` and `strata-core` in this very repo are
     hyphenated distributions with underscored import names -- frob KNOWS this
     distinction internally and does not apply it in the scaffold.
  3. THE SCAFFOLD'S OWN TEST SHIPS BROKEN. tests/system/test_build.py calls
     importlib.import_module with the hyphenated string, so the generated
     project fails its own generated test on first run. That is a positive
     control the scaffold could have used on itself and did not.

WHY OUR DOGFOODING CANNOT SEE IT, which is the same structural blindness behind
today's other consumer findings: this repo is `frob` -- a single word. No
hyphen, so no divergence between distribution and import name, so the bug is
invisible here forever. Compare T-3834 (frob coverage hardcodes `src/frob`,
correct here and wrong everywhere else, filed and re-reported).

SCOPE THE FIX ACROSS ALL SEVEN SCAFFOLD MANIFESTS, not just python-tool. At
least four types carry their own frob.toml.j2 that shadows the shared one, so
per-type verification is required rather than assuming a single template fix
propagates. Check every generated reference to the project name and classify
each as distribution-name or import-name; the bug is that one string is used
for both.

MUST-FIRE FIXTURE:   scaffolding a HYPHENATED name produces an importable
                     package, and the generated test passes.
MUST-STAY-QUIET:     scaffolding a single-word name is byte-identical to today
                     (no regression for the case that currently works).
THIRD FIXTURE:       the generated console script resolves and runs.

ACCEPTANCE
- Distribution name and import name derived separately, everywhere.
- All seven scaffold types checked, with the per-type frob.toml.j2 shadowing
  accounted for.
- A hyphenated scaffold passes its own generated tests end to end -- run it,
  do not reason about it.
- All three fixtures committed.

REPRODUCED ON TODAY'S MAIN, 2026-09-07, AND IT IS WORSE THAN THE ORIGINAL REPORT.
Scaffolded a python-tool named with a hyphen into a temp directory and inspected
the output directly:

    src/my-test-tool/                        hyphenated package DIRECTORY
    pyproject line 20  my-test-tool = "my-test-tool.__main__:main"
    pyproject line 34  my-test-tool = ["py.typed", "logging/config.toml"]
    test_build.py:14   importlib.import_module("my-test-tool")
    test_build.py:21   [sys.executable, "-m", "my-test-tool", "--help"]
    test_build.py:31   from my-test-tool.app import App, AppConfig

THE NEW FINDING: THE GENERATED TEST FILE IS NOT VALID PYTHON. Line 31 is a bare
`from my-test-tool.app import ...`, which is a SyntaxError -- confirmed by
parsing the generated file with ast:

    SyntaxError line 31: invalid syntax
        from my-test-tool.app import App, AppConfig

That changes the severity. The original report said the scaffold's own generated
test FAILS. It does not fail -- it cannot be COLLECTED. A module that raises
SyntaxError at import aborts pytest's collection for that file, so the new user's
first `pytest` run reports a collection error rather than a test failure, and
every other test in that file is never reached. The generated project does not
have a failing suite; it has no runnable suite at all.

WHY THIS MATTERS FOR THE FIX AND NOT JUST THE WRITE-UP: a fix that only
underscores the package DIRECTORY and the console-script target would still leave
line 31 unparseable. The distribution-versus-import split has to be applied to
every generated reference INCLUDING the ones inside generated test source, and
the acceptance check must actually run the generated suite rather than confirm
the package imports. Parse or collect the generated tests as part of the fixture.

SECOND OBSERVATION, ALREADY FILED SEPARATELY: line 34 shows the scaffold
templating a py.typed package-data entry into every generated project. T-4132
records that frob's own copy of that declaration matches no file and is absent
from the built wheel; this confirms the template propagates the same claim
downstream. Do not fix that here -- it is T-4132's -- but do not be surprised by
it either.
