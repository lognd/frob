---
id: T-3984
title: 'F-196..F-208: process tooling audit -- and the subject-count primitive that
  generalises the whole silent-zero class'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: epic
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
Consumer logand.app-v2, F-196..F-208, verbatim from their
docs/security/audit-2026-09-06-process.md. This is the FIFTH audit list from
that repo. T-3919/T-3920/T-3928/T-3942 are the first four, now decomposed into
23 children.

THE HEADLINE IS THE CROSS-CUTTING ASK, NOT THE THIRTEEN ITEMS. In their words:

  "every HIGH here is a gate that is green because it examined nothing -- an
   empty comparison set, an inert query, an unvalidated string, an unresolved
   reference, a step that does not run. frob measures findings; it does not
   measure whether a check had any SUBJECTS. The single highest-value change
   would be for every gate and every repo-side process test to report its
   subject count, and for a zero subject count on a gate configured to be
   enforcing to be a finding in its own right."

THAT IS THE SILENT-ZERO DOCTRINE TURNED INTO A MECHANISM, and it is the most
valuable thing any consumer has sent us. This repo has catalogued the silent-zero
class for months one instance at a time -- a failed measurement rendering as a
clean one. Every one of those instances is the same missing primitive: a gate
reports HOW MANY FINDINGS it produced and never HOW MANY SUBJECTS it examined,
so "0 findings over 0 subjects" and "0 findings over 4000 subjects" are
indistinguishable in every output we have.

WE PROVED THIS OURSELVES TODAY, INDEPENDENTLY. T-3941: PROFILE001 returned the
empty tuple unconditionally on Windows because xref emitted backslash paths that
never matched a forward-slash prefix. It reported a clean tree while measuring
nothing, and it took a FAILING POSITIVE CONTROL to notice. A subject count would
have shown 0-of-N on the first Windows run. The follow-ups T-3947/T-3948 are two
more gates with the same shape. So this is not a consumer preference; it is the
generalisation of a defect we have now confirmed three times in our own code in
one day.

BUILD THE SUBJECT-COUNT PRIMITIVE FIRST, BEFORE ANY OF THE THIRTEEN. Most of the
individual items are instances of it (1, 2, 4, 5, 12 especially). Doing the
primitive first makes several of them cheap or automatic; doing them first
re-implements the same idea thirteen times.

DESIGN CONSTRAINTS worth stating before someone starts:
  - A zero subject count is NOT always a defect. A rule for a language the repo
    does not use legitimately has no subjects. The finding must be "enforcing
    gate with zero subjects", and what counts as enforcing must be explicit --
    otherwise this becomes noise and gets waived, which would be the worst
    outcome.
  - This intersects the two-kinds-of-zero problem already recorded on T-3844:
    zero because the code is clean, versus zero because the condition never
    arose. The subject count is exactly what distinguishes them. Read that
    ticket before designing.

THE THIRTEEN (F-196..F-208 = items 1-13), in the audit's own priority order --
keep that order, they ranked by how much vacuity each removes:
  1  POL000: a policy.pattern matching zero nodes across its whole glob set is
     unproven; a malformed query is a hard config error, not silence.
  2  VMOD002/VMOD003: a test node's runnable must resolve against the union of
     every configured test runner. Already filed by them as F-004/F-013; 141
     unresolved references and two live typos in landed code.
  3  Reproducible evidence: cmd: evidence carries a repo-relative cwd, is re-run
     (or explicitly reported as "claimed, not reproduced") at close and land,
     refuses absolute paths outside the repo, flags the empty-output digest.
  4  TESTRUN001: a configured test runner that produced NO tool result in a run
     is a finding.
  5  Skipped evidence must not count -- the sibling of the xfail item already on
     T-3928. Cross-reference, do not duplicate.
  6  INV000: a frob:invariant naming an unregistered invariant (mirror of
     WAIVE004's stale-waiver rule).
  7  Ratchet the CEILING: the SYS111 lock entry must digest the declared via
     glob list, so widening a may requires an explicit ticketed lock edit.
     Without it "a may is a ceiling" is unenforced.
  8  GEN001: a declared-generated-files block plus a gate that runs its check
     command, replacing three hand-written drift tests.
  9  CI001: CI/local gate parity -- a test runner whose paths no workflow
     references, and min_frob_version cross-checked against the version CI pins.
     THIS ONE IS DIRECTLY OURS TOO: we have an open question about whether the
     three surfaces (CI gates-fast, land --dry-run, real land) run the same
     checks, with no documented relationship.
  10 SEV001: severity overrides take reason/ticket and expire when the ticket
     closes, exactly as frob:waive does.
  11 --only must scope or reject.
  12 TESTMOCK001: where every collaborator of a frob:tests-bound symbol is
     monkeypatched, require at least one non-mocked binding. NOTE this is a
     live defect in OUR code: T-3933 (a synthetic collector lambda proving
     binding while execution stayed unproven) is exactly this shape.
  13 required_file: the inverse of refs.entrypoint, for untracked-but-mandatory
     policy artifacts.

CAREFUL ON ITEM 11 -- I HAVE A PARTIAL MEASUREMENT THAT CUTS BOTH WAYS. Earlier
in this drive I recorded a consumer claim that `--only sys,vmodel` silently runs
everything, then MEASURED it and found the unknown-stage case is REFUSED, and
struck the finding. This audit makes a DIFFERENT claim: that a KNOWN stage name
does not actually filter. My measurement does not refute that and did not test
it. Measure the known-name case specifically before accepting or rejecting item
11, and do not treat my earlier strike as covering it.

GUIDANCE, as with the other four epics: DO NOT BUILD ALL OF IT. Decompose into
leaves, keep the audit's ordering, and file each child naming the finding it
would have caught. VERIFY EACH AGAINST WHAT EXISTS FIRST -- three items across
the previous epics turned out to be already implemented, and a ticket for
existing work is worse than no ticket.

ACCEPTANCE
- The subject-count primitive designed and filed as the first child, with the
  enforcing-gate definition and the T-3844 interaction addressed.
- Thirteen children filed in the audit's order, each naming its finding.
- Items 5 and 12 cross-referenced to T-3928 and T-3933 rather than duplicated.
- Item 11 measured for the known-stage case specifically.