---
id: T-3191
title: 'Local gate typechecks only the host platform: Windows/macOS ty diagnostics
  are unreachable before CI'
state: in-progress
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
- src/frob/process/_reap.py
- src/frob/process/_pid_liveness.py
- src/frob/check/_python.py
- frob.toml
- tests/unit/test_check.py
- docs/modules/process.md
- docs/modules/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/_reap.py
  reason: the two platform-inverted sites; the multi-platform runner scope is added
    by the implementer once the policy is chosen
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/process/_pid_liveness.py
  reason: the two platform-inverted sites; the multi-platform runner scope is added
    by the implementer once the policy is chosen
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/check/_python.py
  reason: 'T-3191: fixing the platform-inverted ty:ignore pair requires wiring multi-platform
    ty into frob check''s _run_ty and declaring the target set in frob.toml'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: frob.toml
  reason: 'T-3191: fixing the platform-inverted ty:ignore pair requires wiring multi-platform
    ty into frob check''s _run_ty and declaring the target set in frob.toml'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_check.py
  reason: 'T-3191: fixing the platform-inverted ty:ignore pair requires wiring multi-platform
    ty into frob check''s _run_ty and declaring the target set in frob.toml'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/process.md
  reason: 'T-3191: doc-edge closure for touched public symbols in _reap.py/_pid_liveness.py/_python.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/check.md
  reason: 'T-3191: doc-edge closure for touched public symbols in _reap.py/_pid_liveness.py/_python.py'
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
STRUCTURAL. CI run 33135896391 failed Typecheck on windows-latest with 4
diagnostics. None of them are reachable from a Linux host, BY CONSTRUCTION.

ROOT CAUSE, MEASURED: `ty check --python-platform` defaults to "the current
system's platform" (confirmed from `ty check --help`). `frob check` never passes
it. So every local gate run, every agent's pre-land check, and every worktree
verification typechecks for Linux ONLY. A Windows-only or macOS-only diagnostic
cannot be observed locally at all -- CI is structurally the first place it can
appear.

THE FOUR DIAGNOSTICS, and why they are a matched pair of opposite errors:

  1. error[unresolved-attribute]: Module `os` has no member `sysconf`
       src/frob/process/_reap.py:798  ->  clk_tck = os.sysconf("SC_CLK_TCK")
     Fine on Linux. Fatal on Windows.

  2. warning[unused-ignore-comment]: Unused `ty: ignore` directive
       src/frob/process/_pid_liveness.py:46
       _kernel32 = ctypes.windll.kernel32  # ty: ignore[unresolved-attribute]
     The suppression is REQUIRED on Linux (no `ctypes.windll` there) and
     FORBIDDEN on Windows (where the attribute resolves, making the ignore
     unused).

  3/4. The same shape, including a self-referential
       `ty: ignore[invalid-argument-type,unused-ignore-comment]`.

THIS IS THE KEY POINT: a single static suppression set CANNOT satisfy both
platforms. Suppressing to make Linux pass creates a Windows failure and vice
versa. Any fix that just edits the four sites will re-break the moment someone
touches platform-conditional code again. The repo already has a recorded lesson
that type-check suppressions must target any consumer's checker, not only the
one this repo happens to run; this is that lesson in its platform form.

WHAT TO BUILD (structural, not four edits):

  1. Make the local gate typecheck EVERY target platform, not just the host.
     `frob check` should run ty once per declared target (linux, win32, darwin)
     -- or resolve `--python-platform all` if that is genuinely sound -- and
     report the union, labelled by platform. Declare the target set in config,
     do not hardcode it: PLATFORM001 doctrine is to declare the boundary, never
     degrade silently.

  2. Decide and implement the POLICY for platform-inverted suppressions, since
     a static ignore provably cannot satisfy all targets. Options to weigh
     explicitly, with the choice justified:
       - keep the platform-conditional import/attribute access behind a
         `sys.platform` guard that ty narrows, so no suppression is needed;
       - a per-platform suppression mechanism if ty supports one;
       - configure `unused-ignore-comment` off, and say plainly what that
         costs (it is a real check -- it catches suppressions that outlived
         their finding, which is exactly the waiver-liveness problem this repo
         already has at a 23.6:1 waive-to-debt ratio).
     Do NOT silently pick the cheapest option.

  3. Fix the four sites under whatever policy is chosen, and verify by running
     the multi-platform check locally -- the fix must be demonstrated from a
     Linux host, not "verified" by pushing and watching CI.

MUST-FIRE FIXTURE: a file with a Windows-only unresolved attribute is caught by
the local gate on a Linux host. That fixture is the whole point -- without it
this regresses the next time someone adds platform-conditional code.

MUST-STAY-QUIET FIXTURE: ordinary cross-platform code produces no new
diagnostics under the multi-platform run, and the check does not become so noisy
that agents start waiving it.

COST NOTE: running ty three times lengthens every `frob check`. Measure the
added wall-clock and report it. If it is material, consider running the
non-host platforms in the land-time/CI-parity gate rather than every check --
but say so explicitly rather than letting it silently not run, which is the
failure mode this ticket exists to fix.

ACCEPTANCE
- `frob check` on a Linux host reports the Windows `os.sysconf` diagnostic
  before any push. Demonstrated.
- The platform-inverted suppression policy is chosen, implemented, documented,
  and justified.
- All four diagnostics from run 33135896391 are resolved under that policy.
- Must-fire and must-stay-quiet fixtures both present.
- Added wall-clock cost measured and stated.
