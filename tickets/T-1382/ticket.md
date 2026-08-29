---
id: T-1382
title: 'Decouple frob from the Makefile: make every workflow a first-class cross-platform
  frob subcommand'
state: queued
kind: feature
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/pyfmt_runner.py
- tests/unit/test_pyfmt_runner.py
- docs/guides/agent-playbook.md
- docs/commands/build.md
- tickets/T-1382/ticket.md
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_pyfmt_runner.py
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/guides/**
  reason: 'TICK009: docs/guides/** matched 35 files; narrow to the one file this pass
    actually edits'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'TICK009: docs/guides/** matched 35 files; narrow to the one file this pass
    actually edits'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/build.md
  reason: 'TICK009: docs/guides/** matched 35 files; narrow to the one file this pass
    actually edits'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'T-1382 is an in-progress UMBRELLA epic whose implementation work is done
    entirely by its leaves (T-2240 landed; T-2241/T-2242 blocked). Holding src/frob/_cli_parsers/**
    meant the parent blocked its OWN children at frob ticket start -- T-2241 needs
    _cli_parsers/_misc.py and __init__.py. Documented epic-lease-leak remedy: narrow
    an umbrella epic to its ledger files so it never holds implementation scope it
    does not itself edit.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tickets/T-1382/ticket.md
  reason: 'T-1382 is an in-progress UMBRELLA epic whose implementation work is done
    entirely by its leaves (T-2240 landed; T-2241/T-2242 blocked). Holding src/frob/_cli_parsers/**
    meant the parent blocked its OWN children at frob ticket start -- T-2241 needs
    _cli_parsers/_misc.py and __init__.py. Documented epic-lease-leak remedy: narrow
    an umbrella epic to its ledger files so it never holds implementation scope it
    does not itself edit.'
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: docs/commands/**
  reason: 'Same: T-2242 needs docs/commands/release.md and was blocked by the parent
    epic''s glob. The leaves declare their own doc files; the umbrella does not edit
    them.'
  actor: logan
  at: '2026-08-16'
body_changes:
- mode: append
  reason: 'record the owner''s scheduling decision (pre-1.0.0, NOT required for the
    incremental cut) and the requested analysis: 18 of ~24 targets are pure frob aliases,
    install/install-tool cannot be frob subcommands because they install frob, so
    the answer is deletion not addition'
  actor: logan
  at: '2026-08-29'
  old_length: 1836
  new_length: 6671
- mode: append
  reason: record the rollup-honesty measurement so the NEEDS CLOSE rot signal is not
    acted on as a real rollup
  actor: logan
  at: '2026-08-29'
  old_length: 6671
  new_length: 9501
- mode: append
  reason: waive the five DOC006 errors this bodys own illustrative non-subcommand
    citations produce
  actor: logan
  at: '2026-08-29'
  old_length: 9501
  new_length: 10911
designated_repro_test: null
acceptance:
- text: GIVEN a repo with no Makefile WHEN every documented frob workflow is run THEN
    each works via a frob subcommand alone
  evidence: []
- text: GIVEN Windows (no make, no POSIX shell) WHEN the coverage workflow runs THEN
    it works without shell quoting, backslash line continuations, or GNU-make syntax
  evidence: []
- text: GIVEN docs and agent guidance WHEN a workflow is described THEN it names the
    frob subcommand, with make targets documented only as thin optional aliases
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User directive 2026-08-01: frob must be cross-project and cross-platform, so it cannot depend on a Makefile.

Current state measured today: the Makefile is 528 lines and 21 call sites across src/frob/ reference it (src/frob/_cli_parsers/_core.py, testing/_collect_cpp.py, vet/_supplychain.py, vet/_capability_registry.py, natives/_build.py, strata/_native_staleness.py, scaffold/_managed.py, scaffold/project.py and others).

The sharpest example is 'make coverage'. Its recipe is ~30 lines of GNU-make-escaped POSIX shell -- COVERAGE_PROCESS_START, a generated coverage rc, an xdist run, a 'node down' grep with a full serial re-run, coverage combine, a T-1363 status guard, then a stamp. None of that runs on Windows, and tests/unit/test_makefile_coverage.py has to slice the recipe text out of the Makefile with a regex and re-run it under bash just to test it -- which is itself evidence the logic is in the wrong place. It should be 'frob coverage', implemented in Python, with the Makefile target reduced to a one-line alias.

Suggested decomposition (leaves to be filed as children):
1. frob coverage -- own the whole recipe in Python, including worker-crash detection and the T-1363 never-promote-partial-data guard.
2. frob build/natives -- replace 'make core' and the native build paths.
3. Audit the 21 Makefile references; each is either a workflow to promote or a scaffold template to re-point.
4. Path/shell portability sweep: no bash -c, no backslash continuations, no assumption of a POSIX shell in any code path.
5. Docs + agent-playbook rewrite so guidance names frob subcommands first; keep make targets as documented optional aliases for muscle memory.

Related: the user's standing preference is still to SUGGEST 'make <target>' where one exists, so this is about removing the DEPENDENCY, not deleting the Makefile.

OWNER DECISION 2026-08-29, plus the analysis it asked for.

SCHEDULING: T-1382 is PRE-RELEASE FOR 1.0.0, and explicitly NOT required for the
incremental release now being cut. Do not work it before the incremental cut; do
not drop it. Its TICK004 age finding is a separate matter -- see T-3399, which
addresses TICK004 erroring on healthy tickets; T-1382 is the one TICK004 finding
that is genuinely correct, and it should keep firing until this is done.

THE OWNER'S EXPLICIT STEER: "make sure whatever solution isn't just bloat;
actually think through the tool's functionality, IF WE EVEN NEED IT AT ALL."

MEASURED, so the eventual implementer does not have to re-derive it. The
Makefile is 574 lines and ~24 targets. Sorted by what they actually run:

ALREADY THIN `uv run frob ...` ALIASES -- these add a second name for an
existing subcommand and nothing else:
    format          frob format --select-imports-only
    lint            frob check --only ruff --skip-ruff-format --only ty
    lint-fix        frob format
    typecheck       frob check --only ty
    test            frob test --all
    test-unit       frob test tests/unit
    test-integration frob test tests/integration
    test-system     frob test tests/system
    sync-skills     frob sync-skills
    clean           frob clean --all -y
    core            frob natives build
    coverage-fast   frob natives build
    pool-warm       frob scaffold pool warm
    pool-lease      frob scaffold pool lease
    pool-status     frob scaffold pool status
    deploy-audit    frob deploy audit
    upload          frob release publish
    playbook        cat docs/guides/agent-playbook.md

REAL CONTENT, not a pure alias:
    coverage        a 3-command sequence:
                    frob ticket reconcile --apply && frob doctor
                    && frob coverage --full
    test-fast       uv run pytest tests/ -q --testmon   (raw pytest; `--testmon`
                    incremental selection has no frob equivalent today)
    all, check      composites over the above

CANNOT BE A FROB SUBCOMMAND, BY CONSTRUCTION:
    install-tool    uv tool install --force --reinstall ".[serve]"
                    --with ./strata-core --with ./frob-core
    install         project dependency sync

THE KEY FINDING, and it answers the owner's question directly: `install-tool`
INSTALLS FROB. A `frob install-tool` subcommand is circular and must never be
built -- if frob is not installed the subcommand does not exist, and if it is
installed you do not need it. This is definitional, not a gap in coverage. The
same is true of `install`. So T-1382's directive ("every workflow a first-class
cross-platform frob subcommand") CANNOT and SHOULD NOT apply to bootstrap.

THEREFORE THE ANSWER IS DELETION, NOT ADDITION. The recommended shape:
  1. DELETE the ~18 alias targets. They carry no logic. Their only effect is to
     give every workflow two names, which is exactly what produced the live
     contradiction this ticket is entangled with: the frob-suggest `make-target`
     hook says "prefer the frob subcommand" while the global instruction says
     "prefer make <target>", and the scaffold SHIPS a Makefile whose `make check`
     the docs tell new users to run (see T-3284).
  2. MOVE the two bootstrap commands into the install documentation as literal
     `uv` invocations. They are two lines of prose, not a build system. This is
     the opposite of bloat -- it removes 574 lines and a dependency on GNU make,
     which is the portability point T-1382 was filed for.
  3. RESOLVE the two real-content targets on their merits:
     - `coverage`: either a `frob coverage --full` that does the reconcile and
       doctor steps itself, or documentation of the three-command sequence. Do
       NOT invent a subcommand whose only job is to run three other subcommands.
     - `test-fast`: `--testmon` incremental selection is genuinely absent from
       `frob test`. That is a real capability gap and the ONLY place in this
       audit where adding something to frob is justified. Decide on its merits,
       separately, and file it if wanted.
  4. The scaffold templates ship their own Makefile. Whatever is decided here
     must apply there too, or new users keep receiving the contradiction.

WHAT NOT TO DO: do not add `frob install-tool`, `frob install`, or a `frob make`
passthrough. Do not port alias targets into subcommands that already exist under
another name. The measure of success for this ticket is LINES AND CONCEPTS
REMOVED, not subcommands added.

OPEN QUESTION FOR WHOEVER TAKES IT: does anything in CI, the scaffold templates,
or the agent playbook depend on a specific `make` target by name? Grep and
report before deleting -- the scaffold's own CI templates and docs reference
`make check`, and T-3277 corrected those docs recently.



ROLLUP HONESTY CHECK, 2026-08-29. fleet_status lists T-1382 as NEEDS CLOSE --
"every child ticket is terminal, write a rollup Done report and close it". DO
NOT DO THAT. A rollup right now would be false, and here is the measurement.

T-1382's real children today are five archived/done tickets: T-2240, T-2241,
T-2242, T-2244, T-2245. All five WIRED Makefile targets to call `frob
<subcommand>` or repointed docs to mention frob first. NONE of them scope the
Makefile for deletion, and none touch the `install-tool`/`install` migration
into install documentation.

Confirmed against current main: the root Makefile is still 574 lines with all
~24 targets present, including every one of the ~18 pure aliases listed in the
breakdown above. So the analysis in this body is NOT stale -- it still matches
main exactly.

CONCLUSION: the decomposition never covered the real work. The children did the
"make the frob subcommands exist" half; nobody ever filed the "delete the now-
redundant aliases and move bootstrap into install docs" half, which is the half
the owner's decision actually calls for. Closing T-1382 would report a
Makefile-decoupling epic as done while the Makefile is undeleted and unchanged.

RELATED PRIOR ART, so this is not re-investigated a third time: T-2959
(archived) diagnosed a DIFFERENT false rollup on this same epic -- T-2384, an
unrelated cross-repo-portability epic, had been mis-parented under T-1382 and
inflated the descendant-walk. T-2959 re-parented it to T-2964, and that fix is
confirmed still in place (tickets/archive/T-2384/ticket.md reads parent:
T-2964). So the current five-child set is genuinely correct; the problem is no
longer a parenting artifact, it is a coverage gap.

WHAT THIS EPIC STILL NEEDS BEFORE IT CAN CLOSE: children covering the deletion
work itself. Per the owner's scheduling decision above, that is PRE-1.0.0 and
explicitly NOT required for the incremental cut -- so file them when that work
is scheduled, not now.

BY-NAME `make` DEPENDENCIES, measured 2026-08-29, for whoever does the deletion:
  .github/workflows/ci.yml     line 50  `run: make core`
                               line 218 `make coverage`
                               lines 196, 241 error text instructing `make coverage`
                               lines 268-269 comment referencing `make install-tool`
  docs/guides/agent-playbook.md line 126 `make core`
                               line 230 `make install-tool`
                               lines 285, 370, 380 `make coverage`
Both are references to the ROOT repo's own Makefile, which the five children
never touched. They are valid today and break the moment the aliases are
deleted. Python scaffold CI and branch-protection templates are clean of `make`.
The cpp scaffold templates reference it legitimately and are out of scope.



DOC006 DISPOSITION for this body's own text, added 2026-08-29 by the
coordinator who wrote the analysis above.

The breakdown above cites `frob install-tool`, `frob install` and `frob make`
as subcommands. None of them resolve, and DOC006 is correct to say so -- it
produced five errors against this file. But they are not broken references to
be repaired: every one appears in a sentence arguing that those subcommands
MUST NEVER EXIST. "do not add `frob install-tool`, `frob install`, or a `frob
make` passthrough" is the conclusion of this ticket's analysis, and
`install-tool` in particular is circular by construction, since it is the
command that installs frob.

Rewriting them to resolve would mean naming real subcommands, which would
invert the argument. Deleting them would delete the finding. So this is
exactly DOC006's documented "intentionally illustrative / future-facing"
case, and it is waived as such rather than fixed.

frob:waive DOC006 reason="this body's `frob install-tool`/`frob install`/`frob \
make` citations are deliberately non-resolving: each appears inside an argument \
that these subcommands must never be built (install-tool is circular by \
construction -- it installs frob). Making them resolve would invert the \
analysis; deleting them would delete the finding. Illustrative-by-design, per \
DOC006's own external/illustrative/future-facing exemption." ticket="T-1382"
