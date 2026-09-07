---
id: T-4145
title: 'the suite is green and the self-gate is not: seven reference errors from adding
  standard community files, plus one oversized module'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
- src/frob/_cli_parsers/_ticket/_closeout.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a repository containing the standard community health files and GitHub
    templates, when the reference gate runs, then it reports no errors and no waivers
    were added for them
  evidence: []
- text: given a genuinely orphaned file that no consumer reads by any convention,
    when the reference gate runs, then REF001 still fires
  evidence: []
- text: given the closeout parser module, when the size gate runs, then it is under
    the threshold and its existing tests still pass
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE TEST SUITE IS GREEN AND THE SELF-GATE IS NOT. CI run 34091766127, ubuntu leg:

    SUITE-RESULT: exitstatus=0 collected=13610 failed=0
    step "frob check (self-gate)": FAILED
    gate-summary: 8 errors, 4750 warnings, 0 unresolved, 934 waived
      FAIL gate:REF     7 errors
      FAIL gate:LARGE   1 error

macOS failed on the identical step. So the only thing standing between this
repository and a green CI run is frob's own gate output about itself.

SEVEN OF THE EIGHT ERRORS WERE INTRODUCED BY ADDING STANDARD COMMUNITY FILES
(T-4131), and that is the finding, not an accident to be waived away:

    REF001  .github/ISSUE_TEMPLATE/config.yml        no inbound references
    REF002  .github/ISSUE_TEMPLATE/bug_report.yml    exactly one (CONTRIBUTING.md)
    REF002  .github/ISSUE_TEMPLATE/feature_request.yml   exactly one (CONTRIBUTING.md)
    REF002  .github/PULL_REQUEST_TEMPLATE.md         exactly one (CONTRIBUTING.md)
    REF002  CONTRIBUTING.md                          exactly one (README.md)
    REF002  SECURITY.md                              exactly one (README.md)
    REF002  CODE_OF_CONDUCT.md                       exactly one (README.md)

EVERY ONE OF THOSE FILES IS CORRECT AND CONVENTIONAL. Their consumer is GITHUB
ITSELF: the platform reads the issue templates, the pull-request template, the
security policy and the code of conduct by PATH CONVENTION. There is no other
in-repo file that should reference them, and adding a second mention purely to
satisfy a reference count would be writing fiction into the docs. REF002's
premise -- "a single point of anchor is fragile" -- is true for a code module and
false for a file whose contract is its location.

THIS IS OUR OWN REPOSITORY REPRODUCING T-3931, the consumer report that a freshly
scaffolded project is not gate-clean on day one. That ticket records this exact
shape: their scaffold fired ROOT001 on the agent-config directory even though the
scaffold's own config declared it, and they worked around it with two
declarations they should not have had to write. We have now hit the same class by
doing the most ordinary thing a project can do -- adding a contributing guide and
a security policy. Our green was evidence of nothing here precisely because we
had none of these files until today.

DO NOT CLEAR THIS BY SPRAYING WAIVERS ACROSS THE SEVEN FILES. T-3931's own
instruction applies verbatim: a project that starts with pre-written waivers
teaches that frob's findings are noise to be waived, which is the habit the rest
of this queue exists to prevent. The right fix is at the source -- these paths
are entry points by convention and the gate should know that, the way it already
knows about other declared entry points.

WHAT TO DO
  1. Teach the reference gate about convention-anchored paths. The community
     health files and the GitHub template paths are consumed by the platform, not
     by a tracked file. Prefer a declaration frob ships and every consumer
     inherits over seven per-file waivers here -- because every consumer repo
     that adds a contributing guide hits exactly this, and T-3931 says so.
  2. Decide whether REF002's one-inbound-reference rule should apply to non-code
     files at all, and record the decision either way. A markdown document
     referenced once from the README is the normal case, not a fragile one.
  3. THE EIGHTH ERROR IS UNRELATED AND SHOULD BE FIXED, NOT WAIVED:
     src/frob/_cli_parsers/_ticket/_closeout.py is 922 lines against an
     800-line threshold. It grew past the limit when T-4106 and T-4108 landed
     their argparse guards. That is a real size finding on a file that has been
     accumulating; split it the way the module's own siblings were split.
  4. Re-run the self-gate after the fix and confirm 0 errors, on CI rather than
     locally -- see the note below about local runs.

A NOTE ON WHERE TO MEASURE, worth recording because it cost this drive a ticket's
worth of wrong conclusions. A local broad run on this machine reported nine test
failures and two worker deaths; CI, on an unloaded machine, reported ZERO test
failures across 13610 tests. The local failures were concentrated in tests that
scan the real repository, and this checkout carries roughly twenty agent
worktrees that CI does not have. Measure self-scan behaviour where the tree is
clean.

MUST-FIRE FIXTURE:   a repository containing the standard community health files
                     and GitHub templates, and nothing else unusual, passes the
                     reference gate with no waivers.
MUST-STAY-QUIET:     a genuinely orphaned file -- one no consumer reads, by
                     convention or otherwise -- still fires REF001.
THIRD FIXTURE:       the closeout parser module is under the size threshold and
                     its behaviour is unchanged, proven by its existing tests.

ACCEPTANCE
- The seven reference errors cleared at the source, with no per-file waivers.
- The decision on REF002 for non-code files recorded either way.
- The oversized module split, not waived.
- The self-gate confirmed at 0 errors on CI.
- All three fixtures committed.
