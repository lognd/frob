---
id: T-3129
title: Stale global frob reports the same version as the project build but has a different
  CLI surface
state: done
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
- src/frob/app/_version_guard.py
- src/frob/__main__.py
- docs/modules/app.md
- tests/unit/test_version_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: acceptance requires the loud warning to actually fire on invocation; wiring
    one call into the existing _print_startup_warnings chain (alongside stale_install_warning/stale_binary_warning)
    is the only place this can be surfaced
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/app.md
  reason: frob:doc directive on binary_fingerprint_warning cites this file; T-1218's
    own precedent doc-lives-here pattern
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_version_guard.py
  reason: new test file for the module this ticket adds
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_version_guard.py
  reason: new test file for the module this ticket adds
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: Record the measured surface divergence under an identical version string
    and the two tickets it caused me to file on false premises
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3595
- mode: set
  reason: Record the measured CLI surface divergence under an identical version string
  actor: logan
  at: '2026-08-27'
  old_length: 3595
  new_length: 3595
evidence:
- tests/unit/test_version_guard.py::test_non_frob_repo_is_quiet
- tests/unit/test_version_guard.py::test_editable_in_tree_run_is_quiet
- tests/unit/test_version_guard.py::test_matching_sha_is_quiet
- tests/unit/test_version_guard.py::test_mismatched_sha_warns_loudly
- tests/unit/test_version_guard.py::test_unresolvable_running_sha_warns
- tests/unit/test_version_guard.py::test_no_frob_spec_is_quiet
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. The globally-installed `frob` on PATH and the project's
own `uv run frob` REPORT THE SAME VERSION STRING but are different builds with
different CLI surfaces:

    $ frob --version                 -> frob 0.530.0
    $ uv run frob --version          -> frob 0.530.0

    $ frob refactor --help           -> {move,rename,split}
    $ uv run frob refactor --help    -> {move,rename,split,move-module}

    $ frob ticket unblock --help     -> invalid choice: 'unblock'
    $ uv run frob ticket unblock --help -> usage: frob ticket unblock ...

So `move-module` and `ticket unblock` BOTH EXIST, and the global binary denies
both while claiming to be the same version.

WHAT THIS COST TODAY, concretely. I am the coordinator and I used bare `frob`
throughout a long session:
- I filed T-3113 ("frob ticket block is add-only: a mistaken blocked_by edge
  cannot be removed without hand-editing the ledger") on a FALSE PREMISE. The
  `unblock` verb has existed since T-2681 landed 2026-08-19. An implementer
  discovered this only after being dispatched against the ticket, and had to
  re-derive the ticket's real content (the genuine gap turned out to be that
  `--reason` was optional and unrecorded).
- I recorded doubt in T-3115 about whether `move-module` still exists, and told
  an agent to check. It exists.
- Every other observation I made with bare `frob` this session is now suspect,
  including a full-repo `frob check` reading of 319 errors that I reported as
  the repo's health floor. That number needs re-taking with `uv run frob`
  before anyone acts on it.

WHY THE VERSION STRING MAKES THIS WORSE THAN AN ORDINARY STALE INSTALL. The
normal defence is "check the version" -- and the version MATCHES. So the one
cheap check a careful operator would run cannot detect this. That is precisely
the failure this repo already recorded in a different subsystem: T-2884 had to
add a git-SHA check to the daemon BECAUSE VERSION STRINGS WERE NOT SUFFICIENT
to detect skew. The same reasoning applies to the CLI itself, and the wheels
epic (T-2501-adjacent packaging work) already names version-coupling-by-gate as
a requirement for the same reason.

It is also the silent-zero shape in its purest form: a verb that exists reports
"invalid choice", which is indistinguishable from a verb that was never built.

WHAT IS WANTED
- A way for `frob` to detect that it is not the build the project expects, and
  say so LOUDLY. A git SHA or build fingerprint compared against the project's
  own, following T-2884's precedent, rather than a version string.
- Consider whether the global install should refuse outright, or warn once per
  invocation, when run inside a project whose own frob differs. Refusing may be
  too strong -- frob is meant to be usable in repos that do not vendor it -- so
  argue the choice.
- The agent playbook and docs should say plainly which invocation is
  authoritative inside this repo. If it is `uv run frob`, bare `frob` should
  not be modelled anywhere in guidance as equivalent.

ACCEPTANCE
- A stale global binary invoked inside this project produces a LOUD, specific
  message naming the mismatch (expected fingerprint vs actual), not a silent
  wrong answer or a bare "invalid choice".
- Must-stay-quiet: the correct build invoked in the same project says nothing.
- The detection does NOT rely on the version string alone; state the mechanism.
- Report whether any other CLI surface differs between the two builds beyond
  `move-module` and `ticket unblock` -- that difference set is the real blast
  radius and nobody has enumerated it.