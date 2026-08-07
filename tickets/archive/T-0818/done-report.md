## Done report

## Done report

Changed:
- tests/system/test_cli_check.py::TestCheckTypescript._make_ts_project
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity.test_render_lint_gate_warns_not_errors_on_gitless_root

Root causes:
1. TestCheckTypescript::test_clean_ts_passes_tsc:
   a. `_make_ts_project` never set a warn-severity `frob.toml`, unlike
      `_make_project` (the python fixture helper) -- TEST001/TEST006 hard
      -errored on the fixture's undocumented/untested `add` symbol.
   b. LANG003 escalates a `KNOWN_GAP` facet to ERROR unless the CHECKED
      repo's own ticket queue independently carries an open ticket for the
      id named in the gap's detail (`frob.lang._support._arch_status`
      names `T-0329` for typescript's `arch` facet) -- verified against
      `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate
      ::test_present_known_gap_with_open_ticket_warns`, which constructs
      exactly this scenario with a synthetic queue. I confirmed T-0329 is
      NOT a dangling/nonexistent reference in the shipped product: it is a
      real, `queued` ticket in this repo's own `tickets.md` (tickets.md,
      `<!-- ticket:T-0329 -->`, EPIC arch multi-language). The failure was
      entirely a fixture gap -- an isolated tmp-path TS project has no
      `tickets.md` at all, so `queue.tickets` is empty and ANY `KNOWN_GAP`
      ticket reference in `frob.lang._support` fails to verify against it,
      by design (same anti-lie posture REG002/REG003 apply to
      `handled_by`/`deferred`). This is the same class of debt T-0719
      already tracks (isolated tmp-path fixtures missing the repo-level
      state a gate needs to resolve cleanly) -- I did not duplicate T-0719,
      I fixed this specific fixture's setup directly since the fix is a
      three-line addition local to this one test class, not the broader
      git-less/queue-less diff-classification mechanism T-0719 owns.
      I did NOT find a genuine dangling/nonexistent-ticket product bug to
      fix in `src/frob/gates/**` or `src/frob/lang/**` -- disclosing this
      plainly since T-0818's dispatch prompt asked for one; the concrete
      "T-0329 is a phantom reference" framing in T-0818's body did not
      hold up under investigation (T-0329 is real and queued). What IS a
      real, broader design question -- whether LANG003's `KNOWN_GAP`
      details, which name FROB's OWN internal roadmap ticket ids, should
      really be verified against every DOWNSTREAM adopting repo's own
      independent ticket queue (an external adopter's queue will almost
      never happen to contain a ticket literally named `T-0329`) -- is out
      of this bug ticket's narrow fixture-debt scope and not something I
      judged safe to redesign under this ticket; noting it here rather
      than silently dropping it.

2. TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root:
   `frob.logging.logger._init()` binds its `StreamHandler`s (via
   `dictConfig`'s `ext://sys.stdout`/`ext://sys.stderr` resolution) to
   whatever stream objects are live the FIRST time `get_logger()` runs in
   the process, and only ever runs once (`_initialized` guard). If an
   earlier test in the same pytest-xdist worker already triggered
   `get_logger()` before this test's `capsys` fixture replaced
   `sys.stderr`, the handler stays bound to the pre-capsys stream forever
   and `capsys.readouterr()` observes nothing -- an order-dependent flake,
   not a logic bug in the assertion itself. Fix: force `frob.logging.
   logger._initialized = False` at the start of the test body (after
   `capsys` is already installed, since it's a fixture argument), so
   `_tracked_python_files`'s first `get_logger()` call inside the test
   re-runs `dictConfig` and rebinds handlers to the CURRENT (capsys
   -patched) streams. Deterministic regardless of what ran earlier in the
   session/worker -- not a reordering, not a flaky marker, not a different
   capture mechanism swap (kept `capsys` per the test's own documented
   rationale for why `caplog` doesn't work here).

Evidence:
- tests/system/test_cli_check.py::TestCheckTypescript::test_clean_ts_passes_tsc
- tests/system/test_cli_check.py::TestCheckTypescript::test_type_error_fails_tsc
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error
- `uv run --frozen pytest tests/system/test_cli_check.py -q` -> 36 passed
  (run 4x in a row post-fix, including once right after `git merge main`,
  to confirm the capsys fix is order-independent, not just lucky).
- Node ids re-confirmed resolvable via
  `uv run --frozen pytest --collect-only -q -o addopts="" tests/system/test_cli_check.py`.

Filed: none (see root-cause 1b's disclosed out-of-scope design question --
judged not safe/appropriate to fix or file speculatively without the
dispatcher's read on whether LANG003's downstream-queue-verification
contract is intended to change; leaving it in this Done report rather than
opening a ticket I'm not confident is correctly scoped).

Gates: `frob check --ticket T-0818` clean across all stage groups (lint,
static, gates-fast, gates-native, gates-security) -- 0 errors in every
group, run AFTER a mid-ticket `git merge main` (playbook 1b) that pulled in
T-0821 and other landed work; re-swept (`frob ticket sweep T-0818`) and
re-verified clean post-merge. `git diff main --diff-filter=D --stat` empty
post-merge (playbook section 9).

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a081356c067c42f95

Deviations: per dispatch instructions, did NOT close or land T-0818; did
NOT bump REL001/version/CHANGELOG (land-owned). Did not find or apply a
`src/frob/gates/**`/`src/frob/lang/**` product-code fix for the T-0329
"dangling reference" framing in T-0818's body -- see root-cause 1b above
for why (T-0329 verified real/queued, not dangling).

### Changed
```
 tests/system/test_cli_check.py | 64 +++++++++++++++++++++++++++++++++++++++++-
 tickets.md                     |  2 +-
 2 files changed, 64 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckTypescript::test_clean_ts_passes_tsc` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckTypescript::test_type_error_fails_tsc` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error` (pytest node id, verified passing when recorded)
