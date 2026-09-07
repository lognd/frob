---
id: T-4155
title: 'the pathspec migration left is_excluded platform-dependent for backslash paths:
  linux says False, Windows says True, and T-4102''s replacement fixture asserts the
  linux answer'
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
path. The migration fixed the CASE half -- `VENDOR/sub/mod.py` against
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
