---
id: T-4013
title: 'F-226: policy globs use fnmatch, so app/**/*.py silently misses files directly
  under app/ and a security policy under-covers in silence'
state: done
kind: security
origin: human
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
- src/frob/policy/__init__.py
- tests/test_policy.py
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_policy.py
  reason: 'T-4013 fix requires: fixture tests in tests/test_policy.py demonstrating
    must-fire/must-stay-quiet/widening-delta behaviour; pathspec added as an explicit
    direct dependency (was only reachable transitively via mypy, a dev dependency
    -- a bare wheel install would ModuleNotFoundError) in pyproject.toml, re-locked
    in uv.lock'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: pyproject.toml
  reason: 'T-4013 fix requires: fixture tests in tests/test_policy.py demonstrating
    must-fire/must-stay-quiet/widening-delta behaviour; pathspec added as an explicit
    direct dependency (was only reachable transitively via mypy, a dev dependency
    -- a bare wheel install would ModuleNotFoundError) in pyproject.toml, re-locked
    in uv.lock'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: uv.lock
  reason: 'T-4013 fix requires: fixture tests in tests/test_policy.py demonstrating
    must-fire/must-stay-quiet/widening-delta behaviour; pathspec added as an explicit
    direct dependency (was only reachable transitively via mypy, a dev dependency
    -- a bare wheel install would ModuleNotFoundError) in pyproject.toml, re-locked
    in uv.lock'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/gates.md
  reason: 'closing scope: load_policy/policy_gate''s frob:doc target lives here; T-4013
    changes documented glob-matching semantics (fnmatch -> pathspec gitwildmatch)'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/modules/gates.md
  reason: gates.md is a huge doc file whose closure balloons scope by 343 unrelated
    anchors; will address the SCOPE002 doc-edge advisory a narrower way instead of
    pulling in the whole file
  actor: logan
  at: '2026-09-06'
evidence:
- tests/test_policy.py::TestRules::test_glob_double_star_matches_file_directly_under_prefix
- tests/test_policy.py::TestRules::test_glob_stays_quiet_outside_matched_directory
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-226, 2026-09-06:

  "Found while fixing H-2 (T-0184): the POL-raw-client-ip glob `app/**/*.py`
   could not match app/request_context.py because fnmatch has no
   zero-or-more-directories `**`. Two silent defects stacked (predicate
   placement and glob semantics) and the rule reported nothing either way."

CONFIRMED BY MEASUREMENT IN OUR OWN CODE, not accepted on report.
src/frob/policy/__init__.py:40 is:

    return tuple(sorted(p for p in snapshot.file_hashes
                        if fnmatch.fnmatch(p, pattern)))

and the behaviour is exactly as described:

    fnmatch("app/request_context.py", "app/**/*.py")  -> False
    fnmatch("app/sub/x.py",           "app/**/*.py")  -> True

So `**` degrades to "at least one intervening directory". A policy author writing
the idiomatic `app/**/*.py` -- which under gitignore/pathspec semantics means
"every .py under app, INCLUDING directly under it" -- silently protects the
subdirectories and leaves the top level unguarded.

WHY THIS IS THE WORST PLACE FOR THIS BUG. These are SECURITY POLICIES. The
consumer's own case is a raw-client-IP policy that failed to cover
request_context.py -- which is precisely the file such a policy exists to police.
The rule did not error, did not warn, and did not report a reduced subject set;
it reported nothing, which is indistinguishable from compliance. A policy that
silently covers less than its author believes is worse than an absent policy,
because it produces confidence.

TWO SILENT DEFECTS STACKED, and the consumer's framing deserves repeating: a
malformed predicate AND an under-matching glob, with the rule reporting nothing
either way. Neither failure had a voice. That is two independent silent zeros in
one rule.

THE FIX: use pathspec/gitwildmatch semantics for policy globs, not fnmatch. That
is what every author will expect, because it is what .gitignore, ruff, and
essentially every modern tool mean by `**`.

BUT TREAT THE CHANGE AS BEHAVIOUR-AFFECTING, NOT A BUGFIX SWAP. Switching
semantics WIDENS what existing patterns match. Some currently-passing policy may
start firing on files it never covered -- which is the correct outcome, and also
a potentially large one-time influx. Measure the delta across this repo's own
policy set BEFORE landing, report the count, and be prepared for the new findings
to be real. Do not suppress them to keep the change small.

CHECK THE OTHER fnmatch CALL SITES WHILE HERE. `git grep -c fnmatch -- src/`
shows eight modules using it: policy, excludes, gates/__init__, _refs,
_doclink_docanchor, _fix_engine_text, ticket_runner/_close_cmd and _query. Each
one that accepts a USER-AUTHORED glob has this same trap; each one that matches
internal fixed patterns does not. Classify all eight and state which are affected
-- fixing only the reported site leaves the same bug in seven other places. NOTE
scope globs are among them, which connects to T-3978 (a scope glob matching zero
tracked files is accepted silently): an under-matching `**` is one way to get a
zero-match scope.

CROSS-REFERENCE, and the consumer makes this point themselves: F-196's POL000
ask -- a policy.pattern matching zero nodes across its whole glob set is
"unproven" and reported -- is filed here as T-3986, and WOULD HAVE SURFACED BOTH
of their stacked defects without anyone diagnosing either. That is the strongest
argument yet for T-3985/T-3986 sequencing ahead of individual rule fixes. Say in
the Done report whether T-3986 would still be needed after this fix (it would --
this fixes one cause of a zero, not the class).

MUST-FIRE FIXTURE: `app/**/*.py` matches a file directly under app/.
MUST-STAY-QUIET: a pattern that should NOT match still does not -- the widening
is bounded and demonstrated, not assumed.
THIRD FIXTURE: the measured before/after finding-count delta across this repo's
own policy set is recorded.

ACCEPTANCE
- gitwildmatch semantics for user-authored policy globs.
- All eight fnmatch call sites classified as affected or not.
- The widening delta measured and reported before landing.
- All three fixtures committed.