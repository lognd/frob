---
id: T-2939
title: 'macOS: git subprocess returncode=128 in test fixtures - 100+ system/CLI test
  failures, root cause unconfirmed'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/system/**
  reason: 'T-2930: narrow to the diagnostic module only; the actual failing test files
    are already tracked by their own tickets (T-1608/1609/1661/2616/2802/2856) and
    this ticket''s job is root-causing the shared gitio failure, not owning every
    test file'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: tests/test_gates.py
  reason: 'T-2930: narrow to the diagnostic module only; the actual failing test files
    are already tracked by their own tickets (T-1608/1609/1661/2616/2802/2856) and
    this ticket''s job is root-causing the shared gitio failure, not owning every
    test file'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: tests/test_serve_leases.py
  reason: 'T-2930: narrow to the diagnostic module only; the actual failing test files
    are already tracked by their own tickets (T-1608/1609/1661/2616/2802/2856) and
    this ticket''s job is root-causing the shared gitio failure, not owning every
    test file'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: tests/test_ticket_leases.py
  reason: 'T-2930: narrow to the diagnostic module only; the actual failing test files
    are already tracked by their own tickets (T-1608/1609/1661/2616/2802/2856) and
    this ticket''s job is root-causing the shared gitio failure, not owning every
    test file'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured on the real macOS runner (T-2917 PR#1 run 32920399634, job
98032723003): the single largest unresolved cluster in the 156-failure
macOS run is 100+ failures across tests/system/test_cli_*.py,
tests/test_gates.py, tests/test_serve_leases.py,
tests/test_ticket_leases.py, tests/test_ticket_land_proof_claims.py,
tests/test_makefile_lock_sync.py, and others, whose common downstream
symptom is a `git` subprocess spawned by `frob.gitio` against a
pytest-fixture-created temp repo returning `returncode=128` (e.g.
`git -C <tmp_path> rev-parse --show-toplevel` / `--abbrev-ref HEAD`),
which frob then correctly surfaces as a loud gitio failure -- the
LOUD-FAILURE behavior itself is working as designed (T-0550's own
"any git failure including no-repo-at-all is a load failure, not a
silent pass" contract); the defect is that `returncode=128` is firing
on a macOS runner for temp repos that DO exist and that the test
fixture DID `git init`+commit successfully moments earlier in the same
test.

VERIFIED NOT the cause (ruled out while triaging T-2930): NOT a
case-insensitive-filesystem string-matching bug (one apparent
"gitio: spawning ('git', '-c', ...)"-lowercase artifact in the raw log
turned out to be pytest's own `r.stdout.lower()` diff rendering, not
corrupted argv -- confirmed by reading the full assertion diff, not
just the summary line).

LEADING HYPOTHESIS (NOT CONFIRMED -- needs a real macOS run to verify,
per this ticket's own instruction not to guess a root cause): git's
"detected dubious ownership in repository" / `safe.directory`
enforcement, which throws exit 128 for a repository whose directory
owner does not match the invoking process's UID -- newer git versions
enable this by default, and a GitHub Actions macOS runner's `/private/
var/folders/...` temp-dir ownership/HOME setup is a plausible trigger
that would not reproduce on the Linux runner if its git version or
default config differs. An alternative candidate: pytest-xdist's
`popen-gwN` worker temp dirs on macOS being created via a different
code path than Linux (timing/race between `git init` and the next
`git` call in a way Linux's faster tmpfs never exposes).

WHY THIS IS THE PRIORITY CLUSTER: it is 100+ of the 156 failures
(the largest by far) and blocks essentially the entire system/CLI test
suite on macOS, not just one subsystem -- until this is root-caused,
no other macOS-only fix can be verified against a clean baseline
system-test run.

NEXT STEP: reproduce on an actual macOS runner (not a guess) with a
single minimal repro -- `git init <dir> && git -C <dir> rev-parse
--show-toplevel` inside the same CI job -- and read the actual stderr
`git` prints (this run's captured stdout only kept frob's own
`gitio: spawning (...) -> returncode=128` summary line, not git's own
stderr text, which is the fastest way to confirm or falsify the
safe.directory hypothesis above). `frob.gitio`'s subprocess wrapper
should also be checked for whether it captures/logs `stderr` from a
failed git invocation at all -- if not, that is itself worth fixing
regardless of this cluster's root cause, since it is the single
biggest diagnostic gap blocking a fast root-cause on the next actual
macOS run.

## Failure log
- 2026-08-28 attempt 1: partial-duplicate check against T-2943/T-2969 (done): NOT a full duplicate. T-2943 fixed only tests/system/test_cli_cycle.py missing-git-init (9/12 failures); T-2969 audited the other 12 test_cli_*.py files, pattern absent in all 12. T-2939's cluster also names tests/test_gates.py, tests/test_serve_leases.py, tests/test_ticket_leases.py, tests/test_ticket_land_proof_claims.py, tests/test_makefile_lock_sync.py -- none touched by T-2943/T-2969. Measured locally on Linux: test_gates.py's only current failure is an unrelated pre-existing drift-lock (TestKnownGateRuleIds, TDD001/VMOD001/VERSION001 missing from _KNOWN_GATE_RULES), not git-128. The other 4 files have zero git_init_and_config/init_repo calls -- plausible match for the same pattern but UNCONFIRMED without a real macOS run (this worktree is Linux-only, cannot reproduce the macOS-specific symptom). Leaving queued: real non-duplicate work remains; needs the ticket's own NEXT STEP (real macOS run with captured git stderr) before a fix can be scoped safely.
