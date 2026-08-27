---
id: T-3116
title: Land's ty gate refuses on pre-existing findings in touched files, manufacturing
  unrelated suppressions
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets-landing.md
- tests/test_ticket_land_ty_diff_attribution.py
- tickets/T-3132/**
evidence_scope:
- tests/test_ticket_land_ty_diff_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/check/_typecheck.py
  reason: declared scope named a file (src/frob/check/_typecheck.py) that has never
    existed in this repo's history; the actual touched-set ty/lint pre-land gates
    measured in this ticket live in src/frob/app/ticket_runner/_land_cmd.py (_assert_touched_files_type_check_pre_land
    et al)
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: declared scope named a file (src/frob/check/_typecheck.py) that has never
    existed in this repo's history; the actual touched-set ty/lint pre-land gates
    measured in this ticket live in src/frob/app/ticket_runner/_land_cmd.py (_assert_touched_files_type_check_pre_land
    et al)
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: T-1907/T-3061's own doc target for this module; will document the new diff-attribution
    behavior alongside the existing pre-land gate docs
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_ticket_land_ty_diff_attribution.py
  reason: T-3116's own new fixtures module (must-fire/must-stay-quiet pair) needs
    write lease + COV/SCOPE coverage
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tickets/T-3132/**
  reason: T-3132 was filed from this same series worktree (auditing T-3116 surfaced
    the sibling lint-gate gap); its ledger dir is part of this worktree's own diff
    until T-3116 lands, so SCOPE001 needs the lease
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: Record the measured line-shift refusal and the suppression-factory dynamic
    it creates
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3225
evidence:
- tests/test_ticket_land_ty_diff_attribution.py::TestTyDiagnosticIdentity::test_ignores_line_and_col
- tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_pre_existing_finding_that_merely_shifted_lines_does_not_refuse
- tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_genuinely_new_finding_still_refuses
- tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_baseline_unmeasurable_falls_back_to_file_scoped_refusal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. While landing T-3106, an agent reported:

    "land's `ty check` refuses on ANY finding in a touched file regardless of
     whether the diff caused it, so I silenced one pre-existing
     `_config_external.py` ty finding my edit merely SHIFTED A FEW LINES."

That is the whole defect in one sentence. The agent's change did not introduce
the finding, did not worsen it, and did not even modify the offending
expression -- it moved it down the file. The gate refused the land anyway, and
the only way through was to add a suppression to code the ticket had no
business touching.

WHY THIS IS SERIOUS RATHER THAN ANNOYING. The repo currently carries 319 `frob
check` errors on main (measured today) and 2117 `frob:waive` directives against
85 `frob:debt`. A gate that demands a suppression as the price of touching a
file is a suppression FACTORY: every ticket that edits a file with a
pre-existing finding must either fix an unrelated defect (scope creep, usually
out of its lease) or silence it (debt, permanently). Neither is what the ticket
was for, and the second is strictly cheaper under time pressure, so the second
is what happens. This mechanism plausibly explains a meaningful share of the
2117.

It also directly contradicts the gate's own stated intent. This is a
"does-not-worsen" gate. Worsening means MORE findings, or the same finding made
harder to fix. A finding that merely relocated is neither.

WHAT IS WANTED: attribute findings to the DIFF, not to the FILE.
- A finding whose identity existed at the parent commit is PRE-EXISTING and
  must not refuse the land, even if its line number moved. Line number is not
  identity -- this repo has already learned that a path/line-shaped identity
  breaks under normalization (T-3065) and that `git blame` dates the TEXT, not
  the finding.
- A finding that is genuinely NEW in the diff still refuses. Do not solve this
  by exempting touched files wholesale; that would turn the gate off.
- The count must not silently increase: if a pre-existing finding is carried
  forward, it stays counted in the repo total, just not charged to this land.

RELATED CONTEXT, do not duplicate: T-3061 added the pre-land ruff lint gate and
is working correctly -- CI lint is green on all three platforms. This ticket is
specifically about the `ty` (type-check) stage's file-scoped attribution, not
about lint, and not about relaxing pre-land verification generally.

ALSO WORTH CHECKING: whether other pre-land stages attribute by FILE rather
than by DIFF. If `ty` does it, siblings may too. Report the audit even if only
one stage is affected.

ACCEPTANCE
- A land that touches a file carrying a pre-existing `ty` finding, without
  introducing or worsening it, SUCCEEDS with no new suppression. Must-stay-quiet
  fixture -- including the line-shift case specifically, since that is the
  measured instance.
- A land that introduces a genuinely new `ty` finding still refuses.
  Must-fire fixture.
- Report how many existing suppressions in the repo appear to have been added
  under this pressure (a suppression whose surrounding change is unrelated to
  the suppressed rule). An estimate with stated method is fine; the point is to
  size the class.