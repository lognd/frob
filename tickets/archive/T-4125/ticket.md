---
id: T-4125
title: a land refused on type errors reproducible in no tree the operator can inspect,
  reporting a bare count with no lines and no statement of which tree it checked
state: done
kind: bug
origin: agent
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land_ty_diff_attribution.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land_ty_diff_attribution.py
  reason: 'T-4125: the pre-land ty refusal message format changed (now names file/line/text,
    tree, commit, and resolved tool path+version); existing fixtures assert against
    it'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'T-4125: the pre-land ty refusal message format changed (now names file/line/text,
    tree, commit, and resolved tool path+version); existing fixtures assert against
    it'
  actor: logan
  at: '2026-09-07'
body_changes:
- mode: set
  reason: 'answers this ticket''s open mechanism question: it is neither the pre-merge
    tree nor a config difference but a bare command name resolving through PATH to
    a different checker VERSION than the project''s own -- confirmed in this repo
    (land runs ty 0.0.58 from PATH while the venv holds 0.0.46). Records the full
    population of 7 bare toolchain invocations, including one file carrying both spellings
    four lines apart, and links the same root cause to T-3887 and the coverage bare-pytest
    report'
  actor: logan
  at: '2026-09-07'
  old_length: 3984
  new_length: 8427
evidence:
- tests/unit/test_project_tool.py::TestProjectToolArgv::test_shape
- tests/unit/vet/test_bare_toolchain.py::TestBareToolchainFindings::test_flags_bare_argv_literal
- tests/unit/vet/test_bare_toolchain.py::TestBareToolchainGate::test_flags_bare_argv_literal
- tests/unit/test_check.py::TestRunRuffRealPaths::test_invokes_ruff_via_project_tool_argv_not_bare_ruff
- tests/unit/test_check.py::TestRunRuffAutofix::test_success_runs_fix_then_format_via_project_tool_argv
- tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix
- tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_genuinely_new_finding_still_refuses
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error
- tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_pre_existing_finding_that_merely_shifted_lines_does_not_refuse
designated_repro_test: null
acceptance:
- text: given a land refused by the type stage, when the refusal is printed, then
    it names each error's file, line and text, plus which tree was checked and the
    commit it was composed against
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error
- text: given a genuine new type error in the ticket's own touched files, when the
    land runs, then it is still refused
  evidence:
  - tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_genuinely_new_finding_still_refuses
- text: given a type error present before the merge with the target branch but absent
    after it, when the land runs, then the land is not refused
  evidence:
  - tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_pre_existing_finding_that_merely_shifted_lines_does_not_refuse
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A LAND REFUSED ON TYPE ERRORS THAT DO NOT EXIST IN ANY TREE THE OPERATOR CAN
INSPECT, AND NAMED NO LINES. Reported as logand.app-v2 F-311. The land reported
that the type checker found 2 NEW errors in the ticket's own touched files, and:

  - the message named NO line numbers and NO error text, only a count
  - running the type checker on the worktree was clean
  - running it after merging main was clean
  - the retry, after merging main, LANDED

So the operator was refused by a measurement they could not reproduce, could not
locate, and could not argue with. They guessed at the cause -- the land's type
stage running on the pre-land canonicalised tree before the merge with main,
which carried a sibling ticket's edits to the same test module, or against a
different checker config -- and their guess is plausible, but the point is that
GUESSING WAS THE ONLY OPTION AVAILABLE TO THEM.

THE DIAGNOSTIC GAP IS THE PRIMARY DEFECT AND SHOULD BE FIXED FIRST, independently
of whatever the underlying tree-selection bug turns out to be. A refusal that
reports a count without the findings is unfalsifiable: it cannot be confirmed,
cannot be reproduced, and cannot be shown to be wrong. The operator's only
recourse is to retry and hope, which is exactly what happened -- and a retry that
succeeds teaches that land refusals are noise to be retried past. That is the
same wrong lesson the scaffold-noise ticket in this queue is about, arriving
through a different door.

WHAT THE MESSAGE MUST CARRY, and this is cheap because the checker already
produced it:
  - the file and line of each error, and its text
  - WHICH TREE was checked, named explicitly: the worktree as written, the
    canonicalised pre-land tree, or the post-merge tree
  - the base or merge commit that tree was composed against
The consumer asked for the first two by name. The third is what makes the report
reproducible by hand.

THE UNDERLYING BUG IS SECONDARY BUT REAL, AND THIS REPO HAS THE SHAPE ON FILE.
Our own record already establishes that a land-time check can read a pre-merge
tree rather than the tree that will actually land, and that a check reading the
wrong tree can fail in either direction. Two candidate mechanisms, both worth
distinguishing rather than assuming:

  (a) The stage checks a tree composed BEFORE the merge with the target branch.
      A sibling ticket's landed edits to the same module are then absent, so a
      reference that resolves after the merge does not resolve before it. This
      matches the consumer's report exactly: their sibling ticket had edited the
      same test module.
  (b) The stage runs with a different checker configuration than a direct
      invocation does. This would make the two measurements incomparable
      regardless of tree.

DETERMINE WHICH BEFORE FIXING EITHER. They need different repairs, and a fix for
(a) applied to a (b) failure would leave the defect in place while looking
resolved.

DO NOT FIX THIS BY RELAXING THE GATE. A pre-merge check that refuses too much is
a bug; a land that stops checking types is worse. If the check must move to the
post-merge tree to be correct, move it -- do not weaken it in place.

MUST-FIRE FIXTURE:   a land refused by the type stage names every error's file,
                     line and text, and names which tree it checked.
MUST-STAY-QUIET:     a land with a genuine new type error in its own touched
                     files is still refused -- the diagnostic improvement must
                     not become a downgrade to a warning.
THIRD FIXTURE:       an error that exists only before the merge with the target
                     branch, and not after, does not refuse the land.

ACCEPTANCE
- The refusal message carries file, line, text, the tree checked, and the commit
  that tree was composed against.
- Mechanism (a) versus (b) determined by measurement and stated.
- The gate is not weakened; if the check moves trees, say which and why.
- All three fixtures committed.

THE OPEN QUESTION ON THIS TICKET IS ANSWERED, AND THE ANSWER IS NEITHER OF MY TWO
CANDIDATES. I proposed (a) the stage checking a pre-merge tree, or (b) a
different checker configuration. The consumer's follow-up (logand.app-v2 F-328)
names the real mechanism, and I then CONFIRMED IT IN THIS REPOSITORY:

    the land's type stage runs a DIFFERENT VERSION OF THE TYPE CHECKER
    than the project itself uses.

MEASURED HERE, 2026-09-07:

    src/frob/app/ticket_runner/_land_cmd.py:4047   cmd = ["ty", "check", ...]
    PATH resolution   /home/logan/.local/bin/ty     ty 0.0.58
    project venv      uv run ty                     ty 0.0.46

A BARE COMMAND NAME resolves through PATH to a globally installed tool, not to
the project's own environment. So the land refuses a ticket on the verdict of a
checker the project does not use and does not pin. Note the direction differs by
machine and is therefore not something a fix can assume: here the PATH copy is
NEWER than the project's (0.0.58 against 0.0.46), while the consumer reports the
opposite (0.0.58 against their venv's 0.0.78). Both are wrong in the same way --
the answer does not come from the project's declared toolchain -- but a fix that
assumes one direction will look correct on one machine and fail on the other.

THIS FULLY EXPLAINS THE ORIGINAL REPORT. The operator's checker was clean on the
worktree and clean after merging main because they ran THEIR ty. The land ran a
different binary at a different version, which produced two diagnostics theirs
does not. That is why the errors were reproducible in no tree they could inspect:
they were not tree-dependent at all. The retry then landed because... the same
skew persisted but the diff had changed. Do not treat the successful retry as
evidence the errors were transient.

THE POPULATION IS LARGER THAN THIS ONE CALL SITE, and the general form is what
should be fixed. Measured across src:

    _land_cmd.py:4047        ["ty", "check", ...]                      bare
    _land_cmd.py:4327        ["ruff", "check", "--output-format", ...] bare
    check/_python.py:136     ["ruff", "check", "--output-format", ...] bare
    check/_python.py:172     ["ruff", "format", "--check", ...]        bare
    check/_python.py:249     ["ruff", "check", "--fix", ...]           bare
    pyfmt_runner.py:226      ["ruff", "check", "--select", "I", ...]   bare
    pyfmt_runner.py:282      ["ruff", "format", "--check", ...]        bare

    pyfmt_runner.py:197      ["uv", "run", "ruff", "check", ...]       correct
    pyfmt_runner.py:253      ["uv", "run", "ruff", "format", ...]      correct

ONE FILE CONTAINS BOTH SPELLINGS, four lines apart. That is the desync this
project exists to prevent, sitting in our own source: two ways to invoke the same
tool, one right and one wrong, with nothing choosing between them.

THIS IS THE SAME ROOT CAUSE AS TWO DEFECTS ALREADY IN THE QUEUE, and they should
be fixed together or at least by one mechanism:
  - T-3887, several gates executing the target project's code in frob's own
    interpreter rather than the project's.
  - The coverage failure a third consumer diagnosed independently: a bare pytest
    resolving to a global shim without the plugins the project depends on, where
    running it through the project's runner with identical arguments succeeds.
Three consumers have now reported the same class from three directions. The fix
is one rule -- never invoke a project's toolchain by bare name -- and it wants a
gate of its own so a fourth spelling cannot appear later.

REVISED GUIDANCE FOR THIS TICKET
- The diagnostic half stands unchanged and is still worth doing first: the
  refusal must name each error's file, line and text, and say which tree it
  checked. Add to that: it must name the RESOLVED TOOL PATH AND VERSION. Had it
  done so, this would have been a five-minute diagnosis instead of a consumer
  round trip.
- Route every toolchain invocation through the project's environment.
- Add a check that fails on a bare toolchain name in an argv literal, so the
  population cannot regrow.

MUST-FIRE FIXTURE (added):  a repository whose PATH holds a different version of
                            the checker than its own environment gets the
                            environment's verdict, not the PATH one.
THIRD FIXTURE (revised):    the refusal message names the resolved tool path and
                            version alongside the findings.