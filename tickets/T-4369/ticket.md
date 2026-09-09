---
id: T-4369
title: check_ticket_mutation_evidence spawns bare uv run pytest against a throwaway
  repo with no project env, silently zero-mutating on macOS
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_mutation_evidence.py
- tests/test_tickets_mutation_evidence.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: test file bound as evidence for the two failing nodeids this fix must pass
  actor: logan
  at: '2026-09-09'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'AFFECT001: check_ticket_mutation_evidence''s affects()-closure doc, updated
    to describe the T-4369 pytest-argv resolution fix'
  actor: logan
  at: '2026-09-09'
body_changes:
- mode: append
  reason: 'BUG002 waiver: designated repro test cannot fail at parent on this Linux
    session -- defect is macOS PATH-content-dependent, same class T-4350 already waived'
  actor: logan
  at: '2026-09-09'
  old_length: 2667
  new_length: 3717
evidence:
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_real_subprocess_spawning_evidence_stays_bounded_not_hung
designated_repro_test: tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED, reproduced locally by simulating the exact macOS CI PATH shape (uv on PATH, .venv/bin not on PATH, no ambient global pytest). src/frob/tickets/_mutation_evidence.py::check_ticket_mutation_evidence builds argv = (uv, run, pytest, *test_ids, -q) (line ~357) and spawns it with cwd=the mutation-evidence sweep's throwaway/fixture repo -- a plain git repo the test harness builds with no pyproject.toml of its own declaring pytest as a dependency. This is the SAME resolution-failure class T-4327/T-4350 already fixed for other call sites (a nested uv run against a project with no environment of its own creates/resolves an empty one and cannot find the tool), left unfixed here because this call site was outside those tickets' declared scope. REPRODUCED LOCALLY: env -i PATH=/tmp/fakebin:/usr/bin:/bin uv run pytest test_m.py::test_add -q (fakebin containing only a uv symlink, no venv/bin, no ambient pytest) fails with error: Failed to spawn: pytest / Caused by: No such file or directory (os error 2), exit 2 -- exactly the shape macOS CI hits (uv present, .venv/bin not on PATH per the CI workflow's direct-interpreter Test step, no global pytest install). Because run_mutations treats a nonzero/failed subprocess result as no confirmatory finding rather than surfacing the spawn failure, the sweep silently reports zero findings instead of erroring or reporting UNMEASURED -- exactly the silent-failure-wearing-a-clean-result shape this project has repeatedly been bitten by. Confirmed as the root cause of these 2 macOS-only failures (CI run 34315257799, head 83a0cecd0): tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged (asserts len(findings) == 1, gets 0), tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_real_subprocess_spawning_evidence_stays_bounded_not_hung (also depends on a real pytest subprocess actually running to observe bounded/unmeasured behavior). FIX: resolve the mutation-test subprocess the same way T-4327/T-4350 standardized on for a throwaway/fixture project with no environment of its own -- invoke the already-running interpreter directly (sys.executable -m pytest) rather than uv run pytest, so it does not depend on the target repo declaring pytest as its own dependency or on PATH/ambient global tool availability. If a spawn genuinely fails after that fix, ensure it surfaces as an error/UNMEASURED finding, not a silent zero -- do not conflate a tool that could not run with a mutant that was not caught. Cannot verify on macOS directly (no macOS access this session); state plainly the CI-green confirmation must come from a macOS run.

frob:waive BUG002 reason="the defect is macOS-only (this repo's macOS CI Test step invokes .venv/bin/python -m pytest directly, so the mutant kill command's uv run pytest cannot resolve pytest without .venv/bin on PATH) and this session has no macOS access; the designated repro test necessarily PASSES at the parent commit on this Linux environment because Linux resolves uv/pytest via ambient PATH and never exhibited the failure at that commit -- the fix is verified by mechanism (the kill argv now resolves via sys.executable -m pytest through resolve_pytest_argv, T-3311's own convention already proven correct for the identical class of defect in T-4327/T-4350) plus a direct reproduction of the exact macOS PATH shape (env -i PATH=/usr/bin:/bin .venv/bin/python -m pytest -q against the two bound evidence tests: FAILS before this fix, PASSES after) and a clean 21/21 local test-file pass, not by a Linux-reproduced fail/pass pair -- the same posture T-4350's own BUG002 waiver already recorded for this identical PATH-content defect class"