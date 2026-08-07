## Done report

Changed:
- src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added COMPLIANCE001-004,
  HOST001, HOST002, HOST-BLAST, KRB001-004, LINT001-005, PII001-004,
  RELWAIVE002, THREAT001-005, and PARSE002 -- 22 ids -- each with a
  citing comment naming the strata/gates module that constructs it.
  PARSE002 landed on `main` concurrently with this ticket's own fix pass
  via a different, unrelated ticket, but was folded straight in here
  rather than parked separately -- it is exactly this ticket's own
  defect class (an emitted-but-unregistered rule id), the file was
  already in scope, and the ticket title covers "missing batch")
- tests/test_gates.py::TestKnownGateRuleIds._KNOWN_ISSUE_ALLOWLIST (drained
  to an empty frozenset -- all 22 ids, including PARSE002, moved to
  `_KNOWN_GATE_RULES` instead of being exempted)
- tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known
  (added a frob:ticket T-0924 edge alongside the existing T-0901 one, since
  its body/allowlist reference changed)

Evidence:
- tests/test_gates.py::TestKnownGateRuleIds (pytest, all 3 tests pass,
  including test_every_emitted_rule_literal_is_known against an EMPTY
  allowlist, re-verified after the PARSE002 fold and again after merging
  main)
- Pre-merge (natives freshly built, this ticket's diff was already
  complete for the T-0903/T-0923/T-0901-batch ids): `uv run frob check
  --only lint/static/gates-fast/gates-native/gates-security/scope/
  prework --ticket T-0924` all clean, 0 errors each, chunked foreground.
- Post-merge (after `git merge main`, which brought in T-0918's
  `derived_state_write_lock` wiring and the unrelated PARSE002 rule):
  `--only lint --ticket T-0924` clean (`ruff format --check
  src/frob/gates/__init__.py tests/test_gates.py` confirms both of THIS
  ticket's touched files are formatted; the 2 files ruff-format flagged
  repo-wide are `src/frob/arch/_lock_ordering.py` /
  `tests/unit/test_arch.py`, brought in by the merge from an unrelated
  ticket, not touched here).
- Post-merge `--only static`, `--only scope`, and `--only prework` could
  NOT be re-run to completion: all three reproducibly hang forever, in
  this worktree and independently confirmed via `lslocks` in several
  OTHER concurrently-running worktrees at the same moment -- a same-
  process self-deadlock in the newly-merged `derived_state_write_lock`
  (T-0918) whenever a gate reaches a `find_clones`/`build_graph`
  rebuild while the outer `frob check` run holds its SHARED
  `derived_state_lock` (confirmed via `lslocks` showing one pid holding
  both READ and blocked WRITE* on its own `.frob/derived.lock`
  simultaneously, and `/proc/<pid>/wchan` = `futex_wait_queue` making
  zero progress over a 500s wait with otherwise-low system load). This
  is a pre-existing environmental regression from a DIFFERENT, already-
  landed ticket (T-0918), entirely outside T-0924's own diff (which only
  touches `_KNOWN_GATE_RULES`'s data and a test file) -- filed as
  CRITICAL bug T-0933 rather than worked around here. Trusting
  the pre-merge clean run for these three gates plus the post-merge
  clean `pytest`/`lint` evidence, since nothing in this ticket's own diff
  touches locking, dup, or graph code.

Filed:
- T-0933 (CRITICAL): `frob check --only scope`/`--only
  prework`/`--only static` self-deadlock on `derived_state_lock`, a
  T-0918 regression -- blocks full gate verification repo-wide until
  fixed.
- T-0932 (PARSE002, filed mid-ticket as a separate gap) was
  dropped with reason "folded into T-0924" once PARSE002 was brought
  into this ticket's own fix instead of being parked separately.

Gates: frob check (chunked --only loop: lint, static, gates-fast,
gates-native, gates-security, scope, prework) clean for T-0924 PRE-MERGE,
0 errors in each group; POST-MERGE, lint and the pytest evidence above
are clean and static/scope/prework are blocked by the newly-filed,
out-of-scope T-0933 deadlock (not a regression from this
ticket's own diff). No waivers added; the allowlist residue is empty (0
ids remain in `_KNOWN_ISSUE_ALLOWLIST`).
