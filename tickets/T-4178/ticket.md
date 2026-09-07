---
id: T-4178
title: the tree walk honours a hardcoded skip list but never consults the repository
  ignore file, so content-reading gates can reach the secrets file
state: queued
kind: security
origin: human
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given an ignored directory absent from the hardcoded skip set, when the tree
    is walked, then it is not yielded
  evidence: []
- text: given a root with no ignore file, when the tree is walked, then behaviour
    is exactly as today
  evidence: []
- text: given a repository whose ignore file lists the secrets file, when any walk
    runs, then that file is not yielded
  evidence: []
threat: info-disclosure
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE TREE WALK HONOURS A HARDCODED SKIP LIST BUT NEVER CONSULTS THE REPOSITORY'S
IGNORE FILE, AND ON THIS CHECKOUT THAT MEANS IT WALKS THE SECRETS FILE. Owner
question: is hardcoding the ignore set the right approach, or should the walk pay
attention to the ignore file? Measured answer below.

THERE ARE TWO WALKS AND ONLY ONE OF THEM IS SAFE.

  `iter_files` -- the shared entry point, 44 call sites, and the one the WALK gate
  points every raw walk at -- PREFERS a `git ls-files` fast path when the root
  looks like a git work tree. That lists TRACKED files only, which is stricter
  than the ignore file: an ignored file is untracked by construction, so it cannot
  appear. This path is already correct and needs nothing.

  `walk_pruned` is the fallback when the root is not a git repo or the git call
  fails, AND it is called directly by callers that bypass `iter_files` entirely.
  It prunes directories by name against a hardcoded frozenset plus the configured
  exclude globs. It has no knowledge of what the ignore file says.

MEASURED ON THIS CHECKOUT, without reading any file's contents -- only checking
whether a path was yielded:

    walk_pruned yielded 9952 files, and DOES yield the secrets file
    iter_files via the git path does NOT yield it

So the secrets file is reachable through one walk and not the other. This
repository carries a standing rule that the secrets file is never read, directly
or indirectly. Two of the direct `walk_pruned` callers READ FILE CONTENTS: the
duplicate-detection scanner and the file-hash gate. A content scanner reaching it
is a rule violation the tool commits on its own initiative, and a finding that
quoted a matched line would put secret material into a report.

WHY THE HARDCODED SET IS STILL RIGHT, AND WHAT IT IS FOR. Do not replace it. It
covers what must be skipped whether or not any ignore file exists -- version
control internals, virtualenvs, caches, build outputs -- and it must work in a
root that is not a git repository at all, which is precisely the case where the
git-based path is unavailable. It is a floor, not a policy.

WHAT IS MISSING IS THE SECOND SOURCE. Compared against this repository's own
ignore file, the hardcoded set omits a coverage HTML output directory, CMake build
directories, several editor and tool state directories, a scratch directory, and
the secrets file itself. None of those are exotic; they are the ordinary contents
of an ignore file. The set also cannot be completed by adding them, because every
consumer's ignore file differs -- which is the entire reason the mechanism exists.

WHAT TO DO
  1. Have `walk_pruned` consult the repository's ignore file in addition to the
     hardcoded floor. The machinery is already present: this module compiles its
     exclude globs with pathspec's gitignore dialect, so parsing ignore patterns
     needs no new dependency and no new matcher.
  2. Honour nested ignore files rather than only the root one, or explicitly state
     that only the root file is read and why. A partial implementation that
     silently skips nested files would be a new silent-zero.
  3. Keep the hardcoded set as a floor that applies unconditionally, including
     when no ignore file exists.
  4. Treat the secrets file as belt-and-braces: it should be excluded once item 1
     lands, but given the standing rule, confirm no content-reading gate can reach
     it by ANY path afterwards, not merely this one.

MUST-FIRE FIXTURE:   an ignored directory that is absent from the hardcoded set is
                     not yielded by the walk.
MUST-STAY-QUIET:     a tracked file matching no ignore rule is still yielded, and
                     a root with no ignore file behaves exactly as today.
THIRD FIXTURE:       in a repository whose ignore file lists the secrets file,
                     no walk yields it.

ACCEPTANCE
- The walk consults the ignore file in addition to the hardcoded floor.
- The nested-ignore-file question decided and stated, not left implicit.
- The hardcoded floor retained and still applied when no ignore file exists.
- No content-reading gate can reach the secrets file by any path, verified rather
  than assumed.
- All three fixtures committed.
