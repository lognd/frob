## Done report

Why: 26 of about 40 live harness shells on 2026-09-23 were poll loops that could never exit, 18 of them `until ! pgrep -f "<literal>"` loops whose pattern is a substring of the polling shell's own `bash -c` command line, so pgrep matched the poller itself for hours after the watched command finished. A PreToolUse hook denies `pgrep -f <literal>` and `ps | grep <literal>` outside quoted or heredoc text, names the four non-self-matching recipes, and takes one override (FROB_SELF_MATCH_ACK=1). `_shellscan.quoted_spans` was added so the guard keeps a quoted argument visible while skipping carried prose (the first draft blocked its own commit message). Registered in the project settings and in the sync MANAGED list; 21 subprocess-contract test cases including the measured poller shapes and the prose false-positive class.

### Changed
```
 .claude/hooks/_shellscan.py               |  11 +++
 .claude/hooks/pgrep-self-match-guard.py   | 134 ++++++++++++++++++++++++++++++
 .claude/hooks/sync-claude-config.py       |   4 +
 .claude/settings.json                     |  11 +++
 docs/guides/claude-hooks.md               |  38 ++++++++-
 tests/test_hook_pgrep_self_match_guard.py | 114 +++++++++++++++++++++++++
 tickets/T-5436/ticket.md        |   9 +-
 7 files changed, 319 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_hook_pgrep_self_match_guard.py::test_self_matching_polls_are_denied` (pytest node id, verified passing when recorded)
- `tests/test_hook_pgrep_self_match_guard.py::test_non_self_matching_recipes_stay_quiet` (pytest node id, verified passing when recorded)
- `tests/test_hook_pgrep_self_match_guard.py::test_override_prefix_and_env_allow` (pytest node id, verified passing when recorded)
- `tests/test_hook_pgrep_self_match_guard.py::test_malformed_payload_is_ignored` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
