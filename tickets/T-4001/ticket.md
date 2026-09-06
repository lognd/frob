---
id: T-4001
title: Two different builds both report 0.530.0, so consumer bug reports cannot be
  checked against main (F-216 was already fixed and unverifiable)
state: queued
kind: bug
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
- src/frob/app/doctor_runner.py
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
WE SHIP BEHAVIOUR CHANGES UNDER AN UNCHANGED VERSION STRING, so a consumer
cannot tell which frob they are running and their bug reports cannot be checked
against our main. Measured today, from a real consumer report.

THE INCIDENT. logand.app-v2 filed F-216: "frob ticket evidence <node-id> cannot
bind vitest node ids at all", and they did the right thing -- they read the
INSTALLED source and reported the mechanism:

  "read _apply_evidence in the installed frob: it calls
   _collect_python_and_rust_ids(root) only, so collected_ids is
   python_ids | rust_ids -- collect_ts_tests is never invoked"

On MAIN that is false. `_apply_evidence` calls `_collect_python_and_rust_ids` at
_verify.py:2675 AND unions `_other_language_collected_ids` at :2698 into the
`collected_ids` it actually passes at :2721. Their installed copy genuinely
lacks the union.

WHY: `git log -S_other_language_collected_ids` shows it arrived in f96a36ae2
(T-3925), landed TODAY. `pyproject.toml` still reads version = "0.530.0" and has
not been bumped. So the installed 0.530.0 and the main-branch 0.530.0 are
DIFFERENT SOFTWARE with the SAME VERSION STRING.

THIS IS T-3129's HAZARD, ESCAPING THE REPO. frob already warns about exactly
this internally -- "the invoked frob binary's source identity does not provably
match this checkout's git HEAD ... `frob --version` alone cannot detect this
(T-3129): version strings can match while the CLI surface and gate logic
differ." We treat that as an in-checkout footgun and tell ourselves to use
`uv run frob`. A CONSUMER HAS NO SUCH OPTION. They install a released frob and
have nothing but the version string.

THE COST IS NOT JUST A WASTED REPORT. It is worse in both directions:
  - We nearly filed a duplicate of work that landed hours earlier. A correct,
    carefully-researched consumer report was UNFALSIFIABLE against our tree.
  - Symmetrically, a report we dismiss as "already fixed" may be describing a
    real gap in the version they actually have. Neither side can tell.
  - Every consumer finding in this queue carrying "frob 0.530.0" is ambiguous
    about WHICH 0.530.0. That is a large population right now.

WHAT TO BUILD -- and note the release-version bump alone does NOT fix this:
1. AN IDENTITY A CONSUMER CAN READ AND REPORT. `frob --version` (and doctor)
   should surface something that distinguishes builds -- a commit sha or build
   id baked at package time -- not only the release version. The in-checkout
   skew warning already computes an identity for this purpose; a packaged wheel
   needs the equivalent, recorded at build rather than derived from a .git it
   will not have.
2. ASK FOR IT IN THE REPORT PATH. Wherever we tell consumers how to file a
   FROBLEMS entry, the build identity should be part of what they paste. This is
   the cheap half and is worth doing even alone.
3. RECONSIDER SHIPPING UNBUMPED. Landing behaviour changes on main under a
   released version number is what makes (1) necessary. Decide deliberately
   whether main between releases should carry a dev/pre-release marker rather
   than the last released number.

DO NOT close this by just bumping to 0.531.0. That fixes today's collision and
recreates it on the next unbumped land. The deliverable is that two different
builds can never present the same identity.

RELATED: the 0.530.0 -> 0.531.0 bump is already a known pending alpha item, and
VERSION001 is expected to hand-fail until T-3916 lands. Sequence this with that
work rather than against it.

MUST-FIRE FIXTURE: two builds from different commits report different
identities.
MUST-STAY-QUIET: a released build reports its release version unchanged for
users who only care about that.

ACCEPTANCE
- A build identity readable from a packaged install with no .git present.
- The consumer report path asks for it.
- An explicit decision on unbumped-main versioning, recorded either way.
- Both fixtures committed.