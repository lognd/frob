---
id: T-3287
title: 'T-3256''s admission registry is per-worktree, so the fleet''s cross-worktree
  checks never see each other: the concurrency divisor is inert exactly where it was
  needed'
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
- tests/unit/test_check_admission.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_admission.py
  reason: must-fire/must-stay-quiet/third fixture tests for the shared cross-worktree
    admission registry
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: set
  reason: 'T-3283: waive the two DOC006 findings on this ticket''s own ephemeral worktree-path
    illustrations (.claude/worktrees/t-3263, t-3264) -- inherently never tracked files,
    per the established per-line frob:waive DOC006 idiom (T-1661/T-2886/T-2962 precedent)'
  actor: logan
  at: '2026-08-28'
  old_length: 3807
  new_length: 4265
- mode: append
  reason: observed a second agent fleet in ../diax holding 4.1GB on the same box;
    records why the memory bound already covers cross-repo contention and the concurrency
    divisor must stay per-repository, so nobody reaches for a global lock
  actor: logan
  at: '2026-08-28'
  old_length: 4265
  new_length: 6756
evidence:
- tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_two_worktrees_of_one_repo_share_one_anchor
- tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_two_worktrees_see_each_others_markers
- tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_non_git_root_falls_back_to_itself
- tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_two_unrelated_repos_do_not_throttle_each_other
- tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_stale_marker_from_dead_pid_does_not_permanently_deflate_shared_budget
- tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_primary_checkout_anchors_to_itself
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3256 landed a cross-process admission budget for `frob check`. Half of it
works. The half that motivated the ticket does not, because the registry is
per-WORKTREE and the contention is cross-worktree.

THE MECHANISM, from the landed code:

    src/frob/check/__init__.py:188
        def _admission_dir(root: Path) -> Path:
            return root / ".frob" / _ADMISSION_DIR_NAME

Every git worktree has its own `.frob/`. So a check running in
<!-- frob:waive DOC006 reason="ephemeral per-session agent worktree path under .claude/worktrees/, never a tracked file (T-3283) -- illustrating the per-worktree registry mechanism with two example worktrees live at filing time, not a live doc pointer" -->`.claude/worktrees/t-3263` registers in that worktree's registry and CANNOT SEE
<!-- frob:waive DOC006 reason="ephemeral per-session agent worktree path under .claude/worktrees/, never a tracked file (T-3283) -- same illustrative mechanism reference as the t-3263 example above" -->a check running in `.claude/worktrees/t-3264`. Each one counts one live check --
itself -- and takes the full machine budget.

MEASURED 2026-08-28 with three agent series live:

    frob check processes running          11
    markers in the primary root registry   1
    markers in every worktree registry     0 (nine worktree dirs, all empty)
    forkservers                           28
    forkserver RSS                        5.3 GB

The nine worktree `.frob/check-admission/` directories EXIST, which proves the
code path runs there -- it is creating a private registry per worktree, not
sharing one.

WHY THIS IS THE CASE THAT MATTERS. T-3256 was filed from a measurement of six
concurrent checks driving the box to zero free memory. Every one of those six
was an agent running `frob check` inside its OWN leased worktree. That is how
this fleet works by design: `frob ticket work <id>` creates a worktree, the
agent checks there. So the exact scenario the ticket was written for is the
scenario the divisor cannot see.

WHAT DOES STILL WORK, and do not regress it: the memory bound is per-process
and unconditional -- `min(cpu, available_mem / per_worker_mb)` applies whether
or not any siblings are visible. A check starting while memory is already tight
still takes a smaller pool. That is real protection and is the most likely
reason the box now shows 28 forkservers at 5.3 GB where the original
measurement showed 51 at 14.5 GB. The concurrency DIVISOR is the inert half,
not the whole mechanism.

THE FIX IS PROBABLY THE GIT COMMON DIR, BUT VERIFY: `git rev-parse
--git-common-dir` resolves to the primary checkout's `.git` from inside any
linked worktree, which is the natural shared anchor. Confirm that is stable for
this repo's layout (worktrees live under `.claude/worktrees/` INSIDE the primary
checkout, which is unusual and may interact badly with a naive parent-walk).
State what you chose and why.

DO NOT FIX THIS BY MAKING THE REGISTRY A GLOBAL /tmp PATH. Two unrelated
checkouts of two different projects on one machine should not throttle each
other, and a world-writable shared path is a permissions and staleness problem.
Anchor it to the repository, not the machine.

CHECK STALENESS HANDLING WHILE YOU ARE THERE. Once the registry is shared, a
marker left by a killed check becomes a phantom concurrent check that shrinks
every sibling's budget permanently. Today's per-worktree registries hide this
because they are almost always empty. Verify the liveness/reaping path is
correct against a PID that died without cleanup -- this repo has a documented
history of orphaned-process records outliving their processes.

MUST-FIRE FIXTURE: two checks running from two DIFFERENT worktrees of the same
repo see each other and each take a reduced budget.
MUST-STAY-QUIET FIXTURE: a single check in a worktree on an idle box still gets
the full budget, and two checks in two UNRELATED repos do not throttle each
other.
THIRD FIXTURE: a stale marker from a dead PID does not permanently deflate live
checks' budgets.

ACCEPTANCE
- The registry is shared across worktrees of one repo; state the anchor used.
- The measurement above re-run with several series live, showing markers > 1.
- The memory bound still applies unchanged.
- All three fixtures present.


CLARIFICATION 2026-08-28, after observing a case the original body did not
anticipate. This SHARPENS the "do not make the registry global" instruction
rather than reversing it -- read both together before choosing an anchor.

OBSERVED: the largest single memory consumer on this box right now is not a
frob process at all. It is a process in a DIFFERENT repository's worktree:

    4181756 KB  /home/logan/projects/diax/.claude/worktrees/t-0037/.venv/bin/python
    1819064 KB  /home/logan/projects/frob/.claude/worktrees/t-3277/.venv/bin/python
    1440952 KB  /home/logan/projects/frob/.claude/worktrees/t-3266/.venv/bin/python -m frob check

The owner is running a second agent fleet in ../diax while this one runs in
frob. Two unrelated repositories are genuinely contending for one machine's
memory, and 4.1 GB of the pressure belongs to neither this repo nor any
`frob check`.

WHY THIS DOES NOT CONTRADICT THE ORIGINAL INSTRUCTION, and why the split
matters:

  MEMORY is a MACHINE resource. It is already handled correctly and globally:
  `_compute_admitted_workers` reads `/proc/meminfo`'s `MemAvailable`, which
  reflects the whole box including diax's 4.1 GB. A frob check starting now
  already sees less available memory because of a process in another repo, and
  sizes down accordingly. Do not change that. It is the half of T-3256 that
  works, and it works precisely because it measures the machine rather than a
  registry.

  CONCURRENCY COUNT is a REPOSITORY question. "How many frob checks are running
  against THIS repo" is what the divisor wants to know, and the answer should
  not change because an unrelated project happens to be busy. A global registry
  would make one repo's activity deflate another's worker budget twice -- once
  through memory, which is correct, and again through the divisor, which is
  double-counting the same contention.

SO THE FIX IS EXACTLY WHAT THE ORIGINAL BODY SAID, no wider: move the anchor
from the WORKTREE to the REPOSITORY. Per-worktree is too narrow (the fleet's
checks never see each other); machine-global is too wide (double-counts, and
adds a permissions and staleness surface). Repository-wide is the correct
grain, and `git rev-parse --git-common-dir` remains the natural candidate.

STATE THIS REASONING IN YOUR DONE REPORT. The next person to look at this will
see two repos fighting over one box and reach for a global lock; the record
should already explain why memory covers that case and the divisor must not.