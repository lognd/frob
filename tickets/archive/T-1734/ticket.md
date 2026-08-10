---
id: T-1734
title: 'Stop-event hook: nudge when a turn diagnoses a defect but files nothing (semantic
  or state-based, never keyword matching)'
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/diagnosis-nudge.py
- .claude/hooks/sync-claude-config.py
- .claude/settings.json
- docs/guides/agent-playbook.md
- tests/test_hook_diagnosis_nudge.py
- tickets/T-1734/ticket.md
- tickets/T-1734/done-report.md
- design/frob.strata
- src/frob/gates/_pii_structural/_keywords.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_hook_diagnosis_nudge.py
  reason: the new hook's own unit+integration tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1734/ticket.md
  reason: 'v2 ledger layout: the ticket''s own per-ticket files are implicitly in
    scope'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1734/done-report.md
  reason: 'v2 ledger layout: the ticket''s own per-ticket files are implicitly in
    scope'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001/SYS100: testsuite node''s may exec/fs.write via-lists must
    declare the new hook test file''s observed capabilities'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_pii_structural/_keywords.py
  reason: PII012's identifier hit on _detect_diagnosis needs the established _PII012_REVIEWED_NON_PII
    allowlist entry (T-0540 precedent) -- an inline frob:waive comment does not suppress
    an IDENTIFIER-name match the way it suppresses a comment-text match
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message
- tests/test_hook_diagnosis_nudge.py::test_ordinary_bug_mention_does_not_nudge
- tests/test_hook_diagnosis_nudge.py::test_stop_hook_active_never_emits
- tests/test_hook_diagnosis_nudge.py::test_rate_limited_within_window
- tests/test_hook_diagnosis_nudge.py::test_recently_filed_ticket_suppresses_nudge
- tests/test_hook_diagnosis_nudge.py::test_probe_removed_from_tracked_repo
designated_repro_test: null
acceptance:
- text: 'OWNER DECISION 2026-08-07: lexical matching is acceptable and an LLM-evaluated
    hook is REJECTED -- do not pipe coordinator messages through a second model. Given:
    a turn ends; when the nudge evaluates it; then no additional model inference is
    performed. The design must therefore be a plain command hook over text and/or
    repo state, and the earlier ''semantic or state-based'' framing in the body is
    superseded on the semantic half.'
  evidence:
  - tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message
  - tests/test_hook_diagnosis_nudge.py::test_ordinary_bug_mention_does_not_nudge
  - tests/test_hook_diagnosis_nudge.py::test_stop_hook_active_never_emits
  - tests/test_hook_diagnosis_nudge.py::test_rate_limited_within_window
  - tests/test_hook_diagnosis_nudge.py::test_recently_filed_ticket_suppresses_nudge
- text: 'The nudge NEVER blocks: it emits systemMessage and exits clean, so a missing
    ticket can never become a stuck session.'
  evidence:
  - tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message
  - tests/test_hook_diagnosis_nudge.py::test_ordinary_bug_mention_does_not_nudge
  - tests/test_hook_diagnosis_nudge.py::test_stop_hook_active_never_emits
  - tests/test_hook_diagnosis_nudge.py::test_rate_limited_within_window
  - tests/test_hook_diagnosis_nudge.py::test_recently_filed_ticket_suppresses_nudge
- text: The nudge names what to file (e.g. 'N findings in X have no owning ticket'),
    not merely that something is unfiled.
  evidence:
  - tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message
- text: 'MEASURED 2026-08-07 via the temporary Stop probe (~/.claude/hooks/_stop-probe.py,
    output at ~/.claude/hooks/state/stop-probe.jsonl): the Stop payload DOES carry
    the response text. Observed keys: _probe_at, background_tasks, cwd, effort, hook_event_name,
    last_assistant_message, permission_mode, prompt_id, session_crons, session_id,
    stop_hook_active, transcript_path. So the state-based fallback described in the
    body is NOT needed -- read last_assistant_message directly.'
  evidence:
  - tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message
  - tests/test_hook_diagnosis_nudge.py::test_ordinary_bug_mention_does_not_nudge
  - tests/test_hook_diagnosis_nudge.py::test_stop_hook_active_never_emits
  - tests/test_hook_diagnosis_nudge.py::test_rate_limited_within_window
  - tests/test_hook_diagnosis_nudge.py::test_recently_filed_ticket_suppresses_nudge
- text: 'Use stop_hook_active to avoid re-entrancy: the payload carries it, and a
    Stop hook that re-triggers itself is the obvious failure mode.'
  evidence:
  - tests/test_hook_diagnosis_nudge.py::test_nudges_on_diagnosis_and_prints_system_message
  - tests/test_hook_diagnosis_nudge.py::test_ordinary_bug_mention_does_not_nudge
  - tests/test_hook_diagnosis_nudge.py::test_stop_hook_active_never_emits
  - tests/test_hook_diagnosis_nudge.py::test_rate_limited_within_window
  - tests/test_hook_diagnosis_nudge.py::test_recently_filed_ticket_suppresses_nudge
- text: 'REMOVE the probe as part of this ticket: delete ~/.claude/hooks/_stop-probe.py,
    its Stop registration in ~/.claude/settings.json, and ~/.claude/hooks/state/stop-probe.jsonl.
    A diagnostic left running is the same residue class this drive has spent the day
    clearing.'
  evidence:
  - tests/test_hook_diagnosis_nudge.py::test_probe_removed_from_tracked_repo
threat: null
component: null
---
A coordinator repeatedly diagnoses a defect in prose -- "this is the same
class as X", "that is a real bug", "the cost structure rewards weak
evidence" -- and then does not file it. Observed several times on
2026-08-07 alone:

- An agent lost ~90 minutes to ten consecutive close timeouts, diagnosed
  the cause precisely, and explicitly decided NOT to file ("a known,
  disclosed mechanism working as designed"). The coordinator overruled it
  and filed T-1727.
- The coordinator itself wrote the perverse-incentive analysis (unbinding
  strong evidence is silent while the honest escape hatch is logged) into
  T-1727's PROSE, then shipped four requirements none of which addressed
  it. It became T-1733 only because the repo owner noticed and asked.

That second one is the shape to design against: the diagnosis was
written down, in a ticket, and still went unenforced. Prose is where
findings go to die. The gap is not knowledge -- it is that nothing
converts a stated finding into a tracked obligation.

WANTED: a Stop-event hook that notices when a turn CONTAINED A DIAGNOSIS
BUT FILED NOTHING, and nudges.

Explicitly NOT keyword matching. "bug", "broken", "should fix" as
substrings will fire on every code review, every Done report, and every
message quoting a ticket title -- and a nudge that fires constantly is
one that gets ignored, which is worse than no nudge. This repo has
already paid for lexical rules three times today (TICK006 on prose about
code spans, a hook blocking its own commit message on a parenthetical, a
hook blocking a correctly-scoped test run).

DESIGN CONSTRAINTS, ESTABLISHED BY MEASUREMENT, NOT ASSUMPTION:

- Prompt-type (LLM-evaluated) and agent-type hooks are documented as
  available only for TOOL events (PreToolUse/PostToolUse/
  PermissionRequest), not Stop. The settings schema does not appear to
  enforce that, so whether a `type: "prompt"` hook fires on Stop must be
  TESTED before the design depends on it.
- A temporary probe is registered on Stop
  (`~/.claude/hooks/_stop-probe.py`) writing observed payload keys to
  `~/.claude/hooks/state/stop-probe.jsonl`. Read it FIRST. The whole
  design hinges on whether the Stop payload carries the assistant's
  response text or only a session id: without the text, no hook of any
  type can judge what the turn said, and the feature has to be built from
  a different signal.
- REMOVE THE PROBE when the real hook lands. A diagnostic left running is
  the same class of residue as everything else this drive has cleaned up.

IF THE RESPONSE TEXT IS AVAILABLE: an LLM-evaluated hook judging "does
this turn state a defect, a root cause, or work that needs doing, for
which no ticket was filed?" is the right implementation, because the
judgement is semantic and a regex cannot make it.

IF IT IS NOT AVAILABLE: fall back to a STATE-BASED signal, which is
better than lexical anyway because it reads actions rather than words.
`.frob/telemetry.jsonl` already records every frob CLI invocation
(`frob.app.telemetry.record_cli_event`), so "did this turn file a
ticket" is answerable exactly, with no parsing. Combine with signals the
repo can measure on its own: findings present with no owning open
ticket; files touched outside every open ticket's scope; `frob:todo`
anchors with no ticket. Nudge on the CONJUNCTION -- work happened,
nothing was filed, and there is unaccounted-for surface.

Either way:

- NUDGE, NEVER BLOCK. A Stop hook that blocks turns a missing ticket into
  a stuck session. Emit `systemMessage`, exit clean.
- Say what to file, not that something is unfiled. "3 findings in
  _coverage_refresh.py have no owning ticket" is actionable; "consider
  filing a ticket" is noise.
- Rate-limit per session so a long turn does not nag repeatedly.

Sibling: T-1725 already gates verb references in the tracked hooks, so
whatever this adds must resolve against the live dispatch table too.

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
