## Done report

A Stop-event hook (`.claude/hooks/diagnosis-nudge.py`) nudges when a turn
states a diagnosis-shaped claim but files no ticket for it -- the gap
named in the ticket body: the finding gets written down and still goes
unenforced because nothing converts a stated diagnosis into a tracked
obligation.

Per the owner's binding decision recorded on the ticket's acceptance
criteria: lexical matching only, no LLM evaluating the turn's text.
`_detect_diagnosis` matches word-boundary-anchored diagnostic-CLAIM
phrasing ("this is a real bug", "root cause is ...", "found a defect",
"should file a ticket") -- never a bare substring, since "bug"/
"broken"/"should fix" alone fire on every code review (the ticket's own
warning, backed by three same-day incidents). `_recently_filed_ticket`
reads `.frob/telemetry.jsonl` for a `frob ticket new` CLI event in the
last 30 minutes -- the state-based half of the conjunction, answerable
exactly, no parsing of prose. The nudge fires only when BOTH hold:
diagnosis-shaped text present, AND no recent ticket-filing event.

Acceptance criteria, addressed directly:
[0] Lexical/state-based only, no LLM inference -- confirmed by design,
    no model call anywhere in the hook.
[1] Never blocks: always exits 0, emits `{"systemMessage": ...}` or
    nothing. Every test asserts `returncode == 0`.
[2] Names what to file: the nudge message includes a ~120-char excerpt
    around the matched diagnosis, not just "something is unfiled" --
    see test_nudges_on_diagnosis_and_prints_system_message.
[3]/[4] `stop_hook_active` read directly from the payload and used to
    suppress re-entrancy (test_stop_hook_active_never_emits);
    `last_assistant_message` read directly, no probe fallback needed.
[5] The probe is removed: `~/.claude/hooks/_stop-probe.py` and
    `~/.claude/hooks/state/stop-probe.jsonl` deleted; its Stop
    registration in `~/.claude/settings.json` replaced with the real
    hook (pointing at the synced `~/.claude/hooks/diagnosis-nudge.py`
    copy, matching how frob-suggest.py/block-backtick-args.py are
    already registered there). This repo's own `.claude/settings.json`
    also registers the hook directly against the repo's own path,
    matching the existing PreToolUse/SessionStart convention in that
    same file. `.claude/hooks/diagnosis-nudge.py` was added to
    `sync-claude-config.py`'s `_MANAGED` list and synced immediately
    (`python3 .claude/hooks/sync-claude-config.py`) so the two copies
    do not drift from the moment this lands. Regression coverage:
    test_probe_removed_from_tracked_repo asserts the probe script is
    gone and the repo's tracked `.claude/settings.json` no longer
    references it.

Rate limiting (T-1734's "must not nag repeatedly" requirement, not a
named acceptance criterion but explicit in the body): one nudge per
`session_id` per 600s, tracked in `~/.claude/hooks/state/
diagnosis-nudge-state.json` -- see test_rate_limited_within_window.

Tested via real subprocess invocation only (matching `tests/
test_telemetry_hook_script.py`'s established pattern for
`scripts/frob-telemetry-hook`), never direct import -- the hook is a
standalone script outside the `frob` package (a hyphenated filename is
not a valid Python module name), and an earlier importlib-based
approach produced spurious ty/DRIFT002 findings that added no real
coverage over the subprocess contract the hook actually exposes.

PII012 on `_detect_diagnosis`: a `frob:waive PII012` comment suppresses
the identifier-sweep's COMMENT-text keyword hits, but does NOT suppress
the hit on the IDENTIFIER NAME itself -- a waiver placed only in the
comment would have looked like a fix while leaving that second finding
live. The correct discharge is the codebase's own established mechanism
for exactly this homonym: `_PII012_REVIEWED_NON_PII`
(`src/frob/gates/_pii_structural/_keywords.py`), the same allowlist
`run_diagnosis` (frob doctor's own diagnostic feature) already uses for
"diagnosis means software, not medical." Added
`(".claude/hooks/diagnosis-nudge.py", "_detect_diagnosis")` there
instead of a second suppression style.

Scope additions beyond the ticket's own declared list: `design/
frob.strata` (SELFAUDIT001/SYS100's `testsuite` node capability
declarations -- the new test file's `subprocess.run`/file-write/
`os.environ`/settings-read usage needed `exec`/`fs.write`/`fs.read`/
`env` `may` entries, same mechanical consequence pattern as
T-1724/T-1768's ledger-file additions), `src/frob/gates/
_pii_structural/_keywords.py` (the allowlist entry above), and
`tickets/T-1734/ticket.md`/`done-report.md` (v2 per-ticket ledger
files).

Process note for whoever reads this next: reset the worktree branch to
main's tip IMMEDIATELY after each successful land, before starting the
next ticket -- never mid-ticket, and never a plain `git merge main` (it
collides with the land-owned-file pre-commit guard on the merge commit
itself, and a stale merge-base makes `frob check --ticket`/`git diff
--diff-filter=D` misattribute already-landed sibling work to the
current ticket). This kept every ticket in this session but one to a
single clean pass; the one exception cost a `git apply --reject` +
manual re-edit round trip when a concurrent land touched the exact
lines my own scope addition needed.

### Changed
```
 .claude/hooks/diagnosis-nudge.py            | 257 ++++++++++++++++++++++++++++
 .claude/hooks/sync-claude-config.py         |   1 +
 .claude/settings.json                       |  12 ++
 design/frob.strata                          |   8 +-
 docs/guides/agent-playbook.md               |  15 ++
 src/frob/gates/_pii_structural/_keywords.py |   5 +
 tests/test_hook_diagnosis_nudge.py          | 190 ++++++++++++++++++++
 tickets/T-1734/done-report.md               |  88 ++++++++++
 tickets/T-1734/ticket.md                    |  79 ++++++++-
 9 files changed, 644 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message` (pytest node id, verified passing when recorded)
- `tests/test_hook_diagnosis_nudge.py::test_ordinary_bug_mention_does_not_nudge` (pytest node id, verified passing when recorded)
- `tests/test_hook_diagnosis_nudge.py::test_stop_hook_active_never_emits` (pytest node id, verified passing when recorded)
- `tests/test_hook_diagnosis_nudge.py::test_rate_limited_within_window` (pytest node id, verified passing when recorded)
- `tests/test_hook_diagnosis_nudge.py::test_recently_filed_ticket_suppresses_nudge` (pytest node id, verified passing when recorded)
- `tests/test_hook_diagnosis_nudge.py::test_probe_removed_from_tracked_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 672 warning(s), 726 waived
- error-findings: PRE001@tickets/T-1734
