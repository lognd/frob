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
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
