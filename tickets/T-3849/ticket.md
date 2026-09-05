---
id: T-3849
title: adopt typani's discarded-Result lint as a frob check stage, then fix the three
  sites it found in frob itself
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: high
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
body_changes:
- mode: append
  reason: 'owner directive: wire typani.lint as a check stage with silent skip when
    unavailable; records the measured CLI surface, JSON output, and the 0.0.3-has-no-lint
    constraint'
  actor: logan
  at: '2026-09-05'
  old_length: 4334
  new_length: 9638
- mode: set
  reason: the bare basename citation resolved against this repo and missed; name the
    sibling-repo file as prose instead of a pointer
  actor: logan
  at: '2026-09-05'
  old_length: 9638
  new_length: 9656
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
typani 0.1's linter (rule TYP003, discarded Result) found three real discarded-
Result bugs in frob 0.530.0 src/ that frob's own gates did not catch. frob has
no equivalent rule. The structural answer is to run that lint on frob itself.

THE THREE FINDINGS, VERIFIED against the source 2026-09-05:

  T-011  src/frob/gates/_coverage.py:1083
             write_coverage_lock(root, filtered)
         Result discarded. A FAILED COVERAGE-LOCK WRITE IS SILENT: the lock is
         the record that a coverage measurement happened, so a failed write
         leaves a stale lock that reads as a current measurement. That is the
         derived-artifact trap this repo has hit before.

  T-012  src/frob/serve/_daemon.py:554
             _poll_verify_worker(root)
         Result discarded (signature at _daemon.py:307, returns
         `Result[WorkerOutcome, WorkerError] | None`). A verify-worker error
         never reaches daemon status, so the daemon reports healthy while its
         worker is failing.

  T-014  `_check_tdd_order` returns `Result[None, LandError]` but is documented
         WARN-only and its result is discarded BY DESIGN. This one is a SMELL,
         not a bug: if the contract is warn-only, the signature is lying and
         should return None (or the discard should be explicit). Decide which;
         do not "fix" it by propagating an error the policy says must not block.

  (T-013, the land-unwind discard, is filed separately as its own critical
   ticket -- it is a data-integrity issue on the land path, not a sweep item.)

ALSO REPORTED, NOT A DEFECT: TYP004 counts 649 instances of
`if x.is_err: return Err(x.danger_err)` in frob src/. That is the idiomatic
propagate in this codebase and 649 is a measure of Result adoption, not of
debt. Do NOT mass-rewrite it. It is recorded here only so the number is not
rediscovered and misread as a finding.

THE STRUCTURAL POINT, WHICH MATTERS MORE THAN THE THREE FIXES. frob's whole
argument is that unaccounted-for work is a build failure, and its own house
rule is that every fallible operation returns a typani Result. But nothing
checks that a returned Result is USED. A discarded Result is precisely the
silent-failure shape frob exists to catch, and frob is currently blind to it in
its own source.

WHAT TO BUILD, after checking what already exists. Search first: frob may
already have a partial rule here (grep the gates registry for anything about
unused return values before concluding it is absent -- "nothing enforces X" is
a claim about code and this repo has been wrong about it before).

If it is genuinely absent, the options, in preference order:
  (a) ADOPT typani's lint directly as a check stage, the way ruff and ty are
      already shelled out to from the Python quality stage. typani is already a
      hard dependency (pyproject `typani>=0.0.3`), the rule already exists and
      is already proven against this codebase -- it found these three. This is
      the cheapest correct answer and it avoids frob reimplementing a rule its
      own dependency ships.
  (b) A native frob gate rule. Only if (a) is impossible, and say why.
Do NOT write a bespoke regex sweep for `^\s*\w+\(` patterns; discarded-Result
detection needs type information, which is exactly why typani's version works
and a lexical one would not (standing directive: token/grammar, never lexical).

SEQUENCING. Land the rule FIRST with the three known findings as its
positive-control denominator, then fix them. A rule that reports zero on a
codebase known to contain three instances is broken, and adopting it after the
fixes would leave that untested.

MUST-FIRE FIXTURE:   a discarded Result is flagged (use one of the three real
                     sites, or a fixture of the same shape).
MUST-STAY-QUIET:     `if x.is_err: return Err(x.danger_err)` is NOT flagged, nor
                     is an explicitly-discarded result where the discard is
                     annotated as deliberate.

ACCEPTANCE
- Existing-rule search reported before anything is built.
- The (a)/(b) choice stated with reasoning.
- The rule landed and measured against the three known sites BEFORE they are
  fixed, with the count stated.
- T-011 and T-012 fixed; T-014's signature-vs-contract mismatch resolved either
  way with the reasoning given.
- Both fixtures committed.



OWNER DIRECTIVE 2026-09-05, which supersedes and sharpens this ticket's original
framing: "There's a new basic lint that I want you to treat the same as the
others (only run if typani import is present, if typani import isn't present,
don't even warn that typani.lint isn't reachable). typani.lint is now a module
though, and I want you to collect the tool results (not sure if there's json
output or junit) into the check verb." Plus: "It might only be in local
../typani".

MEASURED 2026-09-05, so the implementer does not re-derive it:

  INSTALLED typani is 0.0.3 and HAS NO lint MODULE:
      import typani.lint -> ModuleNotFoundError: No module named 'typani.lint'
  The module exists ONLY in the local checkout at ../typani/src/typani/lint/:
      __init__.py  __main__.py  _report.py  _rules.py

  CLI SURFACE (../typani/src/typani/lint/__main__.py):
      --json        emit a JSON array instead of text
      --exclude     glob to exclude (repeatable)
      --select      only keep this rule id
      --ignore      drop this rule id
      --no-info     hide info-severity findings

  OUTPUT: JSON, not junit. typani.lint's own "_report.py::render_json" builds a payload and
  returns `json.dumps(payload)`; "render_text" is the human form. So the answer
  to "json or junit" is JSON, and the collection path is `-m typani.lint --json`.

  (Aside worth noting: typani's own `_report.py` carries a `frob:doc
   docs/lint.md#render_json` directive, so typani is already a frob consumer.)

CONSEQUENCE FOR SEQUENCING, and it is the first thing to settle: frob's pin is
`typani>=0.0.3`, and 0.0.3 does not ship lint. Until a typani release includes
the module, this stage is inert against the published dependency and only ever
runs for someone with a local checkout. Decide explicitly:
  - ship the stage now, inert until typani publishes lint (fine, and it means
    frob is ready the day it lands); or
  - wait for the release and raise the floor at the same time.
Either is defensible. Do NOT add a path-source dependency on ../typani to make
it work locally; that would put a developer-machine path into frob's metadata.

AVAILABILITY BEHAVIOUR -- follow the owner's instruction exactly:
  - `import typani.lint` succeeds  -> run the stage.
  - it fails (typani absent, or too old to have lint) -> SKIP SILENTLY. No
    warning. The owner was explicit: "don't even warn that typani.lint isn't
    reachable".

THE TENSION THIS CREATES, AND MY PROPOSED RESOLUTION -- implement this unless
you find a reason not to, and say which. The owner ALSO set a standing rule
today that there must be "no situation where someone thinks frob has
capabilities that it doesn't have". A silent skip risks exactly that: a clean
`frob check` where the typani lint never ran looks identical to one where it ran
and found nothing -- the silent-zero shape.

These reconcile without a warning, because frob already has the right channel:
`gate:scope-note` already reports what did NOT run and says "status unknown, not
clean". That is not a warning and does not spam; it is the existing
what-was-not-measured line. So: skip silently in the WARNING channel, and name
the skipped stage in the scope-note. The owner's instruction is about not
nagging; the doctrine is about not implying coverage. The scope-note satisfies
both, and it is the precedent already in the codebase.

DISTINGUISH TWO CASES in whatever you report there, because they mean different
things:
  - the target repo does not use typani at all -> the lint is NOT APPLICABLE,
    nothing is missing, and arguably it need not be mentioned at all.
  - the target repo DOES import typani in its source, but typani.lint is not
    importable (old version) -> a real gap: a lint that should have run did not.
    This is the case the owner's earlier tool-not-found rule was written for.
Measure whether the repo imports typani before deciding which case you are in;
"only run if typani import is present" reads most naturally as a property of the
TARGET REPO's code, not merely of frob's environment.

COLLECTION INTO `frob check`:
  - invoke `-m typani.lint --json` and parse the array into the same Violation
    shape every other stage produces, so `--json`, check_summary.py, severity
    overrides and waivers all work uniformly. Do not special-case its output
    downstream.
  - map its severities onto frob's; `--no-info` exists, so it has an info tier
    that frob should probably not surface as a finding by default. Decide and
    state.
  - map its rule ids (TYP003, TYP004 seen in the wild) into the rule-id space
    so `[gates.severity]` can target them. NOTE: this collides with T-3854 --
    `_KNOWN_GATE_RULES` is a closed frozenset of frob's OWN ids, so TYP* ids
    have the same registration problem apollo hit with TOKENS001. Coordinate;
    do not hardcode TYP ids into that frozenset as a shortcut.
  - print the exact argv once, per T-3862's contract.

THE ORIGINAL BODY BELOW STILL APPLIES for the three real findings TYP003 already
made against frob's own source (write_coverage_lock, _poll_verify_worker, and
the `_check_tdd_order` smell), and for the sequencing rule: land the stage FIRST
with those as its positive-control denominator, THEN fix them. A stage that
reports zero against a codebase known to contain three instances is broken.
