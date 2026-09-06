---
id: T-4099
title: 'F-226 follow-up: apply pathspec gitwildmatch fix to remaining 6 fnmatch call
  sites (excludes, gates, refs, close_cmd, query)'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/excludes.py
- src/frob/gates/__init__.py
- src/frob/gates/_refs.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: recording that T-4013's 0->0 widening delta is uninformative because this
    repo has no [policy] table at all -- the fourth dogfooding-blindness instance
    this drive. The remaining sites that ARE exercised here (excludes, graph globs)
    have a measurable delta and must be measured before landing
  actor: logan
  at: '2026-09-06'
  old_length: 2545
  new_length: 5056
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4013 fixed src/frob/policy/__init__.py's user-authored glob matching (fnmatch -> pathspec gitwildmatch): fnmatch has no zero-or-more-directories ** (app/**/*.py silently misses files directly under app/) and is platform-dependent via os.path.normcase (same pattern matches differently on Windows vs Linux). T-4013's Done report classified all 8 repo fnmatch call sites named in its ticket body; the following 6 files/7 call sites are ALSO user-authored-glob call sites carrying the identical trap and were left unfixed (out of T-4013's declared scope, filed here per NO-DUPLICATION/scope discipline):

1. src/frob/excludes.py:83 is_excluded() -- [graph].exclude globs from frob.toml, user-authored. AFFECTED.
2. src/frob/gates/__init__.py:543 _glob_prefix_match() -- [[system]].paths glob, user-authored. AFFECTED.
3. src/frob/gates/__init__.py:1443 _scope_glob_specificity() -- ticket scope globs (via _scope_globs), user-authored; connects directly to T-3978 (a scope glob matching zero tracked files is accepted silently) -- an under-matching ** is one way to produce a zero-match scope. AFFECTED.
4. src/frob/gates/_refs.py:384 _allowlist_covers() -- [[refs.entrypoint]] allowlist globs, user-authored (uses fnmatchcase, so also platform-independent already via case-sensitivity, but still lacks ** semantics). AFFECTED.
5. src/frob/gates/_doclink_docanchor.py:127 -- docs include/exclude globs, user-authored; already carries a waiver comment (WALK001, unrelated rule) that itself documents the exact fnmatch ** gap this ticket would fix. AFFECTED.
6. src/frob/app/ticket_runner/_close_cmd.py:402 _matching_gate_claim_files() -- ticket close evidence criterion glob, user-authored. AFFECTED.
7. src/frob/app/ticket_runner/_query.py:1255 -- ticket scope globs (same _scope_globs expansion as #3), user-authored. AFFECTED.

NOT classified as affected (do not touch under this ticket -- see T-4013's Done report for the full reasoning): src/frob/gates/_fix_engine_text.py:362 mirrors ruff's own per-file-ignores glob dialect specifically (matching what ruff itself would do), not a general policy glob -- switching it to gitwildmatch could DIVERGE from ruff's actual matching behavior rather than fix a bug, so it needs its own investigation into ruff's dialect, not this fix.

Widening caution (same as T-4013): switching a glob-matching call site's semantics WIDENS what existing patterns match. Measure the before/after finding-count delta for each site before landing and report it -- do not suppress new findings to keep a change small.
## THE WIDENING DELTA COULD NOT BE MEASURED HERE, AND THAT IS THE RISK TO CARRY

T-4013 landed the pathspec switch for the policy call site and reported the
before/after finding-count delta as 0 -> 0. The reason matters more than the
number: THIS REPO HAS NO `[policy]` TABLE AT ALL (`grep -c "^\[\[policy" frob.toml`
-> 0). So the delta is zero because the feature is unused here, NOT because the
change is inert.

THAT MEANS THE WIDENING IS UNMEASURED FOR THE PEOPLE IT AFFECTS. Switching
fnmatch -> gitwildmatch makes `app/**/*.py` start matching files directly under
`app/`, which is the whole point -- and every consumer with a `[policy]` table may
see new findings on the next upgrade. We cannot see that from here.

THIS IS THE DOGFOODING BLINDNESS PATTERN AGAIN, now for the fourth time this
drive: hyphenated scaffold names (frob is one word), coverage hardcoding src/frob
(correct here, wrong everywhere), an EMPTY invariants/ directory (so a malformed
invariant file was unthinkable here), and now an absent [policy] table. THE RULE
STANDS: for any feature this repo does not itself exercise, our green is evidence
of nothing -- and here, our ZERO DELTA is evidence of nothing either.

WHAT THIS TICKET SHOULD DO ABOUT IT, in addition to its own seven call sites:
1. When fixing each remaining site, DO NOT report a zero delta from this repo as
   reassurance. Say explicitly whether this repo exercises the feature; if it does
   not, the honest statement is "unmeasured here".
2. For the sites that ARE exercised here (excludes.py and the gates almost
   certainly are -- [graph] exclude globs are used), the delta IS measurable and
   MUST be measured. Those are the ones where a widening could newly red our own
   build, so measure before landing rather than discovering it in CI.
3. Consider whether consumers need a heads-up. A policy glob that silently matched
   less than its author intended has been under-enforcing; after the fix it
   enforces correctly and may surface real findings. That is a good outcome and a
   surprising one, and it is exactly the kind of change a release note exists for.

NOTE ALSO THAT T-4013 ADDED A NEW RUNTIME DEPENDENCY: `pathspec>=0.12`, promoted
from a transitive dev-only dep. That is the right call for correctness, but it
widens the installed wheel's dependency surface -- worth a line in the alpha
checklist, and worth confirming it resolves cleanly in the standalone-install job
(which passed on the run carrying this land, so the signal is good).
