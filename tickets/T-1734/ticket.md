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