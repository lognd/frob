---
id: T-4692
title: 'Gate stages are not verbs: fold dup arch cycle bind perf mutate coverage parse
  pool profile narrative debt deprecated into frob check --only'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4690
parent: T-4687
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/app/check_runner.py
- src/frob/app/dup_runner.py
- src/frob/app/arch_runner.py
- src/frob/app/cycle_runner.py
- src/frob/app/bind_runner.py
- src/frob/app/exports_runner.py
- src/frob/app/perf_runner.py
- src/frob/app/mutate_runner.py
- src/frob/app/coverage_runner.py
- src/frob/app/parse_runner.py
- src/frob/app/pool_runner.py
- src/frob/app/profile_runner.py
- src/frob/app/debt_runner.py
- src/frob/app/deprecated_runner.py
- tests/unit/test_check_only_stages.py
- tests/fixtures/check_stages/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2203
  new_length: 2203
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2203
  new_length: 2203
- mode: set
  reason: '2026-09-19 coordinator review: explore survives; pool/profile/debt/deprecated/parse
    reclassified out of the check --only fold; exports split check/scaffold; ordering
    vs hooks story'
  actor: logan
  at: '2026-09-19'
  old_length: 2203
  new_length: 4434
designated_repro_test: null
acceptance:
- text: Given a committed fixture tree containing a planted duplicate block, when
    frob check --only dup runs on it, then it reports that duplicate -- the same finding
    frob dup reported before the fold (golden comparison, not a no-crash assertion)
  evidence: []
- text: Given frob check --list-stages, when it runs, then it prints exactly the folded
    stages (dup arch cycle bind perf mutate coverage narrative exports) and every
    printed name is accepted by frob check --only; pool, profile, debt, deprecated
    and parse are absent from that list because none of them is a check stage
  evidence: []
- text: Given the exports generate mode, when the check half folds into frob check
    --only exports, then the generate half is reachable under its new home and a test
    exercises it
  evidence: []
acceptance_amendments:
- op: replace
  index: 2
  old_text: Given frob check --list-stages, when it runs, then every folded stage
    name is printed and each printed name is accepted by frob check --only
  new_text: Given frob check --list-stages, when it runs, then it prints exactly the
    folded stages (dup arch cycle bind perf mutate coverage narrative exports) and
    every printed name is accepted by frob check --only; pool, profile, debt, deprecated
    and parse are absent from that list because none of them is a check stage
  reason: '2026-09-19 coordinator review: pool/profile mutate state, debt/deprecated
    are read-only listings that move to T-4695 under explore, parse is a tool-output
    adapter that moves to T-4698 verdict form'
  actor: logan
  at: '2026-09-19'
threat: null
component: cli
labels:
- cli-debloat
- points-3
anchor: false
anchor_reason: null
land_commit: null
---
POINTS: 3. Parent story T-4687. blocked_by T-4690 (needs the shim helper, and
shares _core.py/_misc.py/_reporting.py/__main__.py with it).

PRINCIPLE: a gate stage is not a verb. `frob check` already runs these stages;
having each one ALSO be a top-level verb doubles the surface for zero new
capability, and it is why `frob --help` lists 51 entries.

AMENDED 2026-09-19 (coordinator review): the first version of this ticket swept
`pool`, `profile`, `debt`, `deprecated` and `parse` into `--only`. Measured,
none of the five is a check stage. Corrected classification below.

FOLD INTO `frob check --only <stage>` (these ARE stages -- read-only analyses
that `frob check` already runs and that emit findings):
  dup  arch  cycle  bind  perf  mutate  coverage  narrative
Each keeps a one-minor-version shim (the T-4690 helper) that prints
`frob check --only <stage>` and exits non-zero after the sunset date.

ADD `frob check --list-stages`: prints every stage name, one per line, so the
shims' suggested spelling is discoverable and testable. `--only` already exists
on `frob check`; verify it accepts every folded stage name before deleting the
verb, and add the stage if it does not.

`pool` AND `profile` ARE NOT STAGES -- THEY MUTATE STATE. `frob pool snapshot`
freezes a ratchet baseline and `frob profile` performs the one-way auto-ratchet
downgrade; T-4663 used `frob pool snapshot` as recently as this sprint. Putting
a state-mutating command behind `--only` would be a real footgun: `--only`
reads as "run just this gate", and a reader reasonably expects `frob check
--only pool` to REPORT, not to rewrite the baseline.
DECISION (stated here as the ticket's reason, per the coordinator's "your call
with a reason"): make them SUBVERBS of check -- `frob check pool <op>` and
`frob check profile <op>` -- keeping their own flags and their mutating
semantics intact. This removes two top-level names without lying about what
they do. If the implementer finds the subverb form collides with `check`'s own
positional/flag grammar, the fallback is to leave both as top-level verbs and
record that in the Done report; do NOT force them under `--only`.

`debt` AND `deprecated` MOVE TO T-4695, NOT HERE. They are read-only listings
("list outstanding frob:debt entries", "list outstanding frob:deprecated
entries") and belong with the rest of the read-only analysis surface under
`frob explore`. Do not touch them in this ticket.

`parse` MOVES TO T-4698's VERDICT TABLE, NOT HERE. It is a tool-output adapter
(pytest/ruff/ty/clang/junit -> compact summary), not a gate stage and not
analysis. MEASURED 2026-09-19: `git grep "frob parse "` finds 23 hits, and
every one is in its own implementation (src/frob/_cli_parsers/_core.py,
src/frob/app/parse_runner.py), its own test (tests/unit/test_parse.py), or its
own doc page (docs/commands/parse.md, docs/design/cli-regrouping.md).
.claude/ = 0 hits. scripts/ = 0 hits. No consumer outside itself.

`exports` -- OWNER DECISION 2026-09-19: split it. The CHECK half folds into
`frob check --only exports`. The GENERATE half ("generate __init__.py from
public symbols in a package directory") moves under `scaffold`, NOT refactor.

POSITIVE CONTROL (acceptance): a golden test on a committed fixture tree that
plants a real duplicate block, asserts `frob dup` and `frob check --only dup`
produce IDENTICAL findings on it before the deletion, and after the deletion
asserts `frob check --only dup` still reports the planted duplicate. A test that
only asserts "no crash" does not close this ticket -- the fixture must contain a
finding the tool is REQUIRED to report.

FILES (declared scope):
  src/frob/_cli_parsers/_core.py, _misc.py, _reporting.py, _check.py
  src/frob/__main__.py
  src/frob/app/check_runner.py
  src/frob/app/dup_runner.py, arch_runner.py, cycle_runner.py, bind_runner.py,
  exports_runner.py, perf_runner.py, mutate_runner.py, coverage_runner.py,
  pool_runner.py, profile_runner.py, scaffold_runner.py
  tests/unit/test_check_only_stages.py (new), tests/fixtures/check_stages/ (new)
NOTE: parse_runner.py, debt_runner.py and deprecated_runner.py are NO LONGER in
this ticket's scope -- they belong to T-4698 and T-4695 respectively. The
declared scope on the ledger still lists them from the original filing; the
implementer must run `frob ticket scope T-4692 --remove` for those three (and
`--add scaffold_runner.py`) before starting, or hand them back at close.
