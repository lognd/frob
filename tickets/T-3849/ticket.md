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
