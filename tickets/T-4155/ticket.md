---
id: T-4155
title: 'the pathspec migration left is_excluded platform-dependent for backslash paths:
  linux says False, Windows says True, and T-4102''s replacement fixture asserts the
  linux answer'
state: in-progress
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/excludes.py
- tests/unit/gates/test_ffi_boundary_path_shape.py
- src/frob/gates/_ffi_boundary.py
- tests/test_excludes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/app.md
  reason: 'SCOPE002 closure: is_excluded and its siblings already carry frob:doc/frob:tests
    edges into these files predating T-4155; declaring them closes the scope graph
    per disposition 1 of docs/design/tickets-package-scope-precedent.md'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/_ffi_boundary.py
  reason: 'SCOPE002 closure: is_excluded and its siblings already carry frob:doc/frob:tests
    edges into these files predating T-4155; declaring them closes the scope graph
    per disposition 1 of docs/design/tickets-package-scope-precedent.md'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_excludes.py
  reason: 'SCOPE002 closure: is_excluded and its siblings already carry frob:doc/frob:tests
    edges into these files predating T-4155; declaring them closes the scope graph
    per disposition 1 of docs/design/tickets-package-scope-precedent.md'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/app.md
  reason: 'revert: app.md is a broad shared doc anchoring 200+ unrelated symbols repo-wide
    -- adding it cascades into unrelated scope per docs/design/tickets-package-scope-precedent.md''s
    over-broad-glob trap; is_excluded''s doc-edge into it is accepted WARN-level SCOPE002
    noise (disposition 1), not a closure to chase'
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: set
  reason: 'adds the traced mechanism and the one-argument fix: pathspec derives its
    separator-normalisation set from os.sep/os.altsep at import, so passing an explicit
    separators collection makes matching host-independent. Records that we escaped
    fnmatch''s normcase only to inherit pathspec''s os.sep-derived behaviour, and
    flags the sibling pathspec call site in policy as carrying the same unpinned default'
  actor: logan
  at: '2026-09-07'
  old_length: 4542
  new_length: 6884
- mode: set
  reason: 'same defect as T-4144 in the same batch: an illustrative upper-cased path
    written in path syntax parsed as a live file pointer and failed DOC006 on the
    ubuntu leg. Rewritten as prose'
  actor: logan
  at: '2026-09-07'
  old_length: 6884
  new_length: 6891
designated_repro_test: null
acceptance:
- text: given a backslash-separated relative path and a forward-slash glob, when is_excluded
    is called on linux and on Windows, then both return the same answer
  evidence: []
- text: given an upper-case path and a lower-case glob, when is_excluded is called,
    then it does not match on either platform
  evidence: []
- text: given the chosen contract for backslash input, when a developer reads is_excluded,
    then the contract is stated on the function itself
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE PATHSPEC MIGRATION DID NOT MAKE `is_excluded` PLATFORM-INDEPENDENT. T-4102
replaced fnmatch with pathspec specifically so the same inputs would produce the
same answer everywhere, and rewrote two fixtures around that claim. Both fixtures
STILL FAIL on the Windows leg of CI run 34091766127, and I have measured why.

THE SURVIVING ASSERTION, still in the tree at
tests/unit/gates/test_ffi_boundary_path_shape.py:121 (the exhaustive-handling
copy delegates to it):

    assert is_excluded("vendor\\sub\\mod.py", ("vendor/**",)) is False

MEASURED ON BOTH PLATFORMS, same code, same pathspec version:

    linux    is_excluded('vendor\\sub\\mod.py', ('vendor/**',))  ->  False
    windows  is_excluded('vendor\\sub\\mod.py', ('vendor/**',))  ->  True

So the function still answers differently per platform for a backslash-containing
path. The migration fixed the CASE half -- an upper-cased vendor path against
`vendor/**` is now False on linux, which fnmatch would have matched on Windows --
and left the SEPARATOR half intact. pathspec's gitwildmatch evidently normalises
separators on Windows; on posix a backslash is an ordinary filename character.

WHY THE REWRITE MISSED IT, and this is the part worth learning rather than just
fixing: T-4102 correctly identified that the ORIGINAL fixture asserted a false
premise about fnmatch, then wrote a replacement asserting "a backslash-joined rel
never matches a POSIX glob". That is a NEW claim about a NEW library, and it was
verified the same way the old one was -- by reasoning on linux. The ticket's own
lesson was that simulating a platform's paths does not simulate its stdlib. The
rewrite reproduced the identical error one library over. A claim about
platform-conditional behaviour is unproven until it runs on that platform, and
that applies to the replacement as much as to the thing being replaced.

WHAT THE RIGHT ANSWER IS, and it is not "assert True on Windows". The real
question this fixture should be asking is whether a backslash path is a supported
input at all. Every producer in this repo was fixed to emit POSIX-relative paths
precisely so `is_excluded` never sees a backslash -- that was T-3941/T-3947/
T-3948/T-4107's work. So the fixture is asserting behaviour for an input the
system is designed never to produce, and it is asserting a value that differs by
platform. Both halves are wrong.

TWO DEFENSIBLE FIXES. PICK ONE DELIBERATELY AND SAY WHY:
  a. NORMALISE AT THE BOUNDARY. `is_excluded` converts backslashes to forward
     slashes before matching, making the answer identical everywhere and making
     the function robust against any producer that regresses. Then the assertion
     becomes True on both platforms and the fixture states something true and
     useful.
  b. DELETE THE BACKSLASH ASSERTION. Declare a backslash path unsupported input,
     document it on the function, and let the producer-side POSIX guarantee carry
     the contract. Then the fixture tests only supported inputs.
Option (a) is the safer of the two given this repo's history -- producers HAVE
regressed on this exact axis five times, and a normalising boundary turns the
sixth into a non-event. But it is a real decision about where the contract lives,
so make it explicitly.

DO NOT RESOLVE THIS BY MARKING THE FIXTURES WINDOWS-SKIP. That would restore the
original silence: the whole reason these two exist is that this repo could not
see its own Windows behaviour, and skipping them there re-creates that blindness
in the one place it has already cost us twice.

MUST-FIRE FIXTURE:   `is_excluded` returns the SAME answer on linux and Windows
                     for every input the repo can produce, including a
                     backslash-separated one, proven by the assertion running on
                     both legs rather than by reasoning on one.
MUST-STAY-QUIET:     a genuinely non-matching path still returns False, and the
                     case-sensitivity fix T-4102 landed is not regressed
                     (an upper-case path does not match a lower-case glob).
THIRD FIXTURE:       whichever contract is chosen is stated on the function
                     itself, so the next producer author can see it.

ACCEPTANCE
- The platform divergence for backslash input eliminated, by normalisation or by
  declaring the input unsupported, with the choice justified.
- The case-sensitivity behaviour T-4102 landed proven unregressed.
- Neither fixture skipped on Windows.
- The chosen contract documented on the function.
- All three fixtures committed.

MECHANISM CONFIRMED, WITH THE EXACT LEVER TO PULL. I traced why the answer
differs, so nobody has to rediscover it:

    pathspec.util.NORMALIZE_PATH_SEPS  ->  []   on this linux box
    os.sep = '/'   os.altsep = None

    normalize_file('vendor\\sub\\mod.py')                    -> 'vendor\\sub\\mod.py'
    normalize_file('vendor\\sub\\mod.py', separators=['\\']) -> 'vendor/sub/mod.py'

pathspec derives its separator-normalisation set FROM THE HOST OS at import time.
On posix `os.altsep` is None so the set is empty and a backslash is an ordinary
filename character. On Windows `os.sep` is a backslash and `os.altsep` is a
forward slash, so the set is non-empty and pathspec rewrites backslashes to
forward slashes before matching. Hence True there and False here, from identical
code.

THE FIX IS ONE ARGUMENT: `normalize_file` (and the matching entry points that
call it) accept an explicit `separators` collection. Passing one makes the result
deterministic and host-independent, as the second line above demonstrates. That
is almost certainly preferable to normalising the string ourselves before calling
pathspec -- it keeps one normalisation instead of two, and it cannot drift out of
step with whatever pathspec does internally.

AND HERE IS THE LESSON THAT OUTLIVES THIS TICKET, which I want recorded because
this project has now made the same mistake twice in the same file. We migrated
from fnmatch to pathspec specifically to escape a host-derived behaviour --
fnmatch runs both operands through `os.path.normcase`, which folds case and
rewrites separators on Windows. We landed on a library whose separator handling
is ALSO derived from the host, just through a different attribute
(`os.sep`/`os.altsep` rather than `normcase`). The migration removed the
case-folding half and preserved the separator half, and we called it
platform-independent because we only measured the half that changed.

SO THE RULE IS NOT "PREFER LIBRARY X OVER LIBRARY Y". It is: any matcher that
reads the host's path conventions is platform-dependent until you pin those
conventions explicitly. When this lands, check the OTHER pathspec call site
(`src/frob/policy/__init__.py`, migrated earlier under a separate ticket) for the
same unpinned default -- it will have inherited the identical defect, and nothing
has measured it on Windows either.
